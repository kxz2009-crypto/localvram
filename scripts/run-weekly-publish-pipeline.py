#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OLLAMA_ENDPOINT = "http://127.0.0.1:11434"

TRANSIENT_ERROR_PATTERNS = (
    "429",
    "too many requests",
    "timed out",
    "timeout",
    "connectex",
    "connection reset",
    "connection refused",
    "temporary failure",
    "tls handshake timeout",
    "eof",
)
LOGGER = configure_logging("run-weekly-publish-pipeline")


def emit(message: str, *, level: str = "info", stderr: bool = False, flush: bool = False) -> None:
    _ = (stderr, flush)
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


def parse_retry_delays(raw: str) -> list[int]:
    out: list[int] = []
    for piece in (raw or "").split(","):
        piece = piece.strip()
        if not piece:
            continue
        out.append(max(0, int(piece)))
    return out or [5, 10, 20]


def is_transient_error(stderr: str) -> bool:
    text = (stderr or "").lower()
    return any(token in text for token in TRANSIENT_ERROR_PATTERNS)


def run_gh(gh_path: str, args: list[str], retry_delays: Iterable[int], allow_retry: bool = True) -> subprocess.CompletedProcess[str]:
    retries = list(retry_delays) if allow_retry else []
    cmd = [gh_path, *args]
    attempt = 0
    while True:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return proc
        if attempt >= len(retries) or not is_transient_error(proc.stderr):
            return proc
        delay = retries[attempt]
        attempt += 1
        emit(
            f"gh command failed ({proc.returncode}), retrying in {delay}s: {' '.join(args)}",
            level="warning",
            stderr=True,
        )
        time.sleep(delay)


def assert_gh_auth(gh_path: str, retry_delays: Iterable[int]) -> None:
    proc = run_gh(gh_path, ["auth", "status", "-h", "github.com"], retry_delays, allow_retry=True)
    if proc.returncode != 0:
        raise RuntimeError("gh auth is not ready; run 'gh auth login -h github.com -p https -w'")


def parse_run_id_from_stdout(stdout: str) -> int | None:
    match = re.search(r"/actions/runs/(\d+)", stdout or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def latest_workflow_run_id(
    gh_path: str,
    repo: str,
    workflow: str,
    retry_delays: Iterable[int],
    event: str = "workflow_dispatch",
) -> int | None:
    proc = run_gh(
        gh_path,
        ["api", f"repos/{repo}/actions/workflows/{workflow}/runs?event={event}&per_page=5", "--jq", ".workflow_runs[0].id"],
        retry_delays,
        allow_retry=True,
    )
    if proc.returncode != 0:
        return None
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def find_new_workflow_run_id(
    gh_path: str,
    repo: str,
    workflow: str,
    baseline_id: int | None,
    started_at: datetime,
    retry_delays: Iterable[int],
    poll_interval_s: int,
    poll_timeout_s: int,
    event: str = "workflow_dispatch",
) -> int:
    deadline = time.time() + max(10, poll_timeout_s)
    while time.time() < deadline:
        proc = run_gh(
            gh_path,
            ["api", f"repos/{repo}/actions/workflows/{workflow}/runs?event={event}&per_page=10"],
            retry_delays,
            allow_retry=True,
        )
        if proc.returncode != 0:
            time.sleep(max(1, poll_interval_s))
            continue
        try:
            payload = json.loads(proc.stdout or "{}")
        except Exception:  # noqa: BLE001
            payload = {}
        runs = payload.get("workflow_runs") or []
        for run in runs:
            run_id = run.get("id")
            created_at_raw = str(run.get("created_at") or "")
            if not isinstance(run_id, int):
                continue
            if baseline_id is not None and run_id == baseline_id:
                continue
            try:
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except ValueError:
                created_at = None
            if created_at is not None and created_at < started_at:
                continue
            return run_id
        time.sleep(max(1, poll_interval_s))
    raise RuntimeError(f"timed out waiting for workflow run id: {workflow}")


def watch_run(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int]) -> bool:
    proc = run_gh(gh_path, ["run", "watch", str(run_id), "-R", repo, "--exit-status"], retry_delays, allow_retry=True)
    if proc.stdout.strip():
        emit(proc.stdout.strip())
    if proc.returncode != 0 and proc.stderr.strip():
        emit(f"watch_warning={proc.stderr.strip()}", level="warning", stderr=True)
    return proc.returncode == 0


def run_view_field(gh_path: str, repo: str, run_id: int, field: str, retry_delays: Iterable[int]) -> str:
    proc = run_gh(
        gh_path,
        ["run", "view", str(run_id), "-R", repo, "--json", field, "--jq", f".{field}"],
        retry_delays,
        allow_retry=True,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def print_failure_hint(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int], label: str) -> None:
    proc = run_gh(gh_path, ["run", "view", str(run_id), "-R", repo, "--log-failed"], retry_delays, allow_retry=True)
    if proc.returncode != 0:
        emit(f"{label}_failure_hint=unable_to_fetch_failed_logs run_id={run_id}", level="warning")
        return
    text = (proc.stdout or "").strip()
    if not text:
        emit(f"{label}_failure_hint=no_failed_logs run_id={run_id}", level="warning")
        return

    failure_class = ""
    failure_detail = ""
    for line in text.splitlines():
        m = re.search(r"failure_class=([a-z0-9_]+)", line, re.IGNORECASE)
        if m:
            failure_class = m.group(1).strip().lower()
        m = re.search(r"failure_detail=(.+)$", line, re.IGNORECASE)
        if m:
            failure_detail = m.group(1).strip()
        m = re.search(r"FailureClass::([a-z0-9_]+)\s*-\s*(.+)$", line, re.IGNORECASE)
        if m:
            failure_class = m.group(1).strip().lower()
            failure_detail = m.group(2).strip()

    if failure_class:
        emit(f"{label}_failure_class={failure_class}")
    if failure_detail:
        emit(f"{label}_failure_detail={failure_detail}")

    focus_tokens = (
        "Ollama preflight",
        "failure_class=",
        "failure_detail=",
        "FailureClass::",
        "ollama_",
        "required_targets_",
        "model_missing",
        "ollama_not_visible",
    )
    focus_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if any(token.lower() in line.lower() for token in focus_tokens):
            focus_lines.append(line)
    if focus_lines:
        emit(f"{label}_failure_log_excerpt_begin")
        for line in focus_lines[-20:]:
            emit(line)
        emit(f"{label}_failure_log_excerpt_end")
    emit(f"{label}_failure_log_command=gh run view {run_id} -R {repo} --log-failed")


def dispatch_weekly(
    gh_path: str,
    repo: str,
    workflow: str,
    include_heavy_targets: bool,
    extra_targets: str,
    benchmark_timeout_s: str,
    retry_delays: Iterable[int],
    poll_interval_s: int,
    poll_timeout_s: int,
) -> int:
    baseline = latest_workflow_run_id(gh_path, repo, workflow, retry_delays, event="workflow_dispatch")
    started_at = datetime.now(timezone.utc)

    args = ["workflow", "run", workflow, "-R", repo]
    if include_heavy_targets:
        args.extend(["-f", "include_heavy_targets=true"])
    if str(extra_targets).strip():
        args.extend(["-f", f"extra_targets={str(extra_targets).strip()}"])
    if str(benchmark_timeout_s).strip():
        args.extend(["-f", f"benchmark_timeout_s={str(benchmark_timeout_s).strip()}"])

    proc = run_gh(gh_path, args, retry_delays, allow_retry=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to dispatch weekly benchmark workflow")
    if proc.stdout.strip():
        emit(proc.stdout.strip())

    run_id = parse_run_id_from_stdout(proc.stdout)
    if run_id is None:
        run_id = find_new_workflow_run_id(
            gh_path=gh_path,
            repo=repo,
            workflow=workflow,
            baseline_id=baseline,
            started_at=started_at,
            retry_delays=retry_delays,
            poll_interval_s=poll_interval_s,
            poll_timeout_s=poll_timeout_s,
            event="workflow_dispatch",
        )
    emit(f"weekly_run_id={run_id}")
    emit(f"weekly_run_url=https://github.com/{repo}/actions/runs/{run_id}")
    return run_id


def dispatch_smoke(
    gh_path: str,
    repo: str,
    workflow: str,
    endpoint: str,
    required_targets: str,
    restart_if_empty: str,
    retry_delays_s: str,
    retry_delays: Iterable[int],
    poll_interval_s: int,
    poll_timeout_s: int,
) -> int:
    baseline = latest_workflow_run_id(gh_path, repo, workflow, retry_delays, event="workflow_dispatch")
    started_at = datetime.now(timezone.utc)

    args = ["workflow", "run", workflow, "-R", repo]
    if endpoint.strip():
        args.extend(["-f", f"endpoint={endpoint.strip()}"])
    if required_targets.strip():
        args.extend(["-f", f"required_targets={required_targets.strip()}"])
    if restart_if_empty.strip():
        args.extend(["-f", f"restart_if_empty={restart_if_empty.strip()}"])
    if retry_delays_s.strip():
        args.extend(["-f", f"retry_delays_s={retry_delays_s.strip()}"])

    proc = run_gh(gh_path, args, retry_delays, allow_retry=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to dispatch runner smoke check workflow")
    if proc.stdout.strip():
        emit(proc.stdout.strip())

    run_id = parse_run_id_from_stdout(proc.stdout)
    if run_id is None:
        run_id = find_new_workflow_run_id(
            gh_path=gh_path,
            repo=repo,
            workflow=workflow,
            baseline_id=baseline,
            started_at=started_at,
            retry_delays=retry_delays,
            poll_interval_s=poll_interval_s,
            poll_timeout_s=poll_timeout_s,
            event="workflow_dispatch",
        )
    emit(f"smoke_run_id={run_id}")
    emit(f"smoke_run_url=https://github.com/{repo}/actions/runs/{run_id}")
    return run_id


def run_publish_wrapper(
    gh_path: str,
    repo: str,
    source_run_id: int,
    apply_retirement_candidates: str,
    retirement_min_stale_runs: int,
    retirement_max_seen_ok_count: int,
    retry_delays_s: str,
) -> None:
    script = ROOT / "scripts" / "run-publish-workflow.py"
    cmd = [
        sys.executable,
        str(script),
        "--gh-path",
        gh_path,
        "--repo",
        repo,
        "--source-run-id",
        str(source_run_id),
        "--apply-retirement-candidates",
        apply_retirement_candidates,
        "--retirement-min-stale-runs",
        str(retirement_min_stale_runs),
        "--retirement-max-seen-ok-count",
        str(retirement_max_seen_ok_count),
        "--retry-delays-s",
        retry_delays_s,
    ]
    emit("dispatch_publish_command=" + " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError("publish wrapper failed")


def wait_auto_publish_workflow_run(
    gh_path: str,
    repo: str,
    workflow: str,
    retry_delays: Iterable[int],
    poll_interval_s: int,
    poll_timeout_s: int,
) -> int:
    baseline = latest_workflow_run_id(gh_path, repo, workflow, retry_delays, event="workflow_run")
    started_at = datetime.now(timezone.utc)
    run_id = find_new_workflow_run_id(
        gh_path=gh_path,
        repo=repo,
        workflow=workflow,
        baseline_id=baseline,
        started_at=started_at,
        retry_delays=retry_delays,
        poll_interval_s=poll_interval_s,
        poll_timeout_s=poll_timeout_s,
        event="workflow_run",
    )
    emit(f"auto_publish_run_id={run_id}")
    emit(f"auto_publish_run_url=https://github.com/{repo}/actions/runs/{run_id}")
    return run_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch Weekly Benchmark and optionally auto-chain Publish Benchmark Artifact.")
    parser.add_argument("--gh-path", default="gh")
    parser.add_argument("--repo", default=os.getenv("LV_GH_REPO", "kxz2009-crypto/localvram"))
    parser.add_argument("--weekly-workflow", default="weekly-benchmark.yml")
    parser.add_argument("--skip-publish", action="store_true")
    parser.add_argument("--include-heavy-targets", action="store_true")
    parser.add_argument("--extra-targets", default="")
    parser.add_argument("--benchmark-timeout-s", default="")
    parser.add_argument("--retry-delays-s", default=os.getenv("LV_NETWORK_RETRY_DELAYS_S", "5,10,20"))
    parser.add_argument("--poll-interval-s", type=int, default=5)
    parser.add_argument("--poll-timeout-s", type=int, default=180)
    parser.add_argument("--apply-retirement-candidates", choices=["true", "false"], default="false")
    parser.add_argument("--retirement-min-stale-runs", type=int, default=3)
    parser.add_argument("--retirement-max-seen-ok-count", type=int, default=2)
    parser.add_argument("--run-smoke-on-weekly-failure", choices=["true", "false"], default="true")
    parser.add_argument("--smoke-workflow", default="runner-smoke-check.yml")
    parser.add_argument(
        "--smoke-endpoint",
        default=os.getenv("LV_OLLAMA_ENDPOINT") or os.getenv("OLLAMA_HOST") or DEFAULT_OLLAMA_ENDPOINT,
    )
    parser.add_argument("--smoke-required-targets", default="")
    parser.add_argument("--smoke-restart-if-empty", choices=["true", "false"], default="true")
    parser.add_argument("--smoke-retry-delays-s", default="")
    parser.add_argument("--retry-weekly-after-smoke", choices=["true", "false"], default="false")
    parser.add_argument(
        "--publish-mode",
        choices=["auto", "manual", "auto-then-manual"],
        default="auto",
        help="auto: wait workflow_run publish only; manual: always dispatch publish wrapper; auto-then-manual: fallback to manual when auto publish run is not found in time.",
    )
    parser.add_argument("--publish-workflow", default="publish-benchmark-artifact.yml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    retry_delays = parse_retry_delays(args.retry_delays_s)
    try:
        emit("phase=auth_check", flush=True)
        assert_gh_auth(args.gh_path, retry_delays)
        emit("phase=dispatch_weekly", flush=True)
        weekly_run_id = dispatch_weekly(
            gh_path=args.gh_path,
            repo=args.repo,
            workflow=args.weekly_workflow,
            include_heavy_targets=bool(args.include_heavy_targets),
            extra_targets=str(args.extra_targets),
            benchmark_timeout_s=str(args.benchmark_timeout_s),
            retry_delays=retry_delays,
            poll_interval_s=int(args.poll_interval_s),
            poll_timeout_s=int(args.poll_timeout_s),
        )
        emit(f"phase=watch_weekly run_id={weekly_run_id}", flush=True)
        watch_ok = watch_run(args.gh_path, args.repo, weekly_run_id, retry_delays)
        if not watch_ok:
            emit("watch_status=nonzero_continue_to_conclusion_check", level="warning", flush=True)
        emit(f"phase=weekly_completed run_id={weekly_run_id}", flush=True)
        conclusion = run_view_field(args.gh_path, args.repo, weekly_run_id, "conclusion", retry_delays).lower()
        emit(f"weekly_conclusion={conclusion or 'unknown'}")
        if conclusion != "success":
            print_failure_hint(args.gh_path, args.repo, weekly_run_id, retry_delays, label="weekly")
            smoke_conclusion = ""
            if args.run_smoke_on_weekly_failure == "true":
                emit("phase=dispatch_smoke_after_weekly_failure", flush=True)
                smoke_retry_delays_s = str(args.smoke_retry_delays_s).strip() or str(args.retry_delays_s).strip()
                smoke_run_id = dispatch_smoke(
                    gh_path=args.gh_path,
                    repo=args.repo,
                    workflow=str(args.smoke_workflow),
                    endpoint=str(args.smoke_endpoint),
                    required_targets=str(args.smoke_required_targets),
                    restart_if_empty=str(args.smoke_restart_if_empty),
                    retry_delays_s=smoke_retry_delays_s,
                    retry_delays=retry_delays,
                    poll_interval_s=int(args.poll_interval_s),
                    poll_timeout_s=int(args.poll_timeout_s),
                )
                emit(f"phase=watch_smoke run_id={smoke_run_id}", flush=True)
                smoke_watch_ok = watch_run(args.gh_path, args.repo, smoke_run_id, retry_delays)
                if not smoke_watch_ok:
                    emit("watch_status=smoke_nonzero_continue_to_conclusion_check", level="warning", flush=True)
                smoke_conclusion = run_view_field(args.gh_path, args.repo, smoke_run_id, "conclusion", retry_delays).lower()
                emit(f"smoke_conclusion={smoke_conclusion or 'unknown'}")
                if smoke_conclusion != "success":
                    print_failure_hint(args.gh_path, args.repo, smoke_run_id, retry_delays, label="smoke")
            if args.retry_weekly_after_smoke == "true" and smoke_conclusion == "success":
                emit("phase=retry_weekly_after_smoke", flush=True)
                retry_weekly_run_id = dispatch_weekly(
                    gh_path=args.gh_path,
                    repo=args.repo,
                    workflow=args.weekly_workflow,
                    include_heavy_targets=bool(args.include_heavy_targets),
                    extra_targets=str(args.extra_targets),
                    benchmark_timeout_s=str(args.benchmark_timeout_s),
                    retry_delays=retry_delays,
                    poll_interval_s=int(args.poll_interval_s),
                    poll_timeout_s=int(args.poll_timeout_s),
                )
                emit(f"phase=watch_weekly_retry run_id={retry_weekly_run_id}", flush=True)
                retry_watch_ok = watch_run(args.gh_path, args.repo, retry_weekly_run_id, retry_delays)
                if not retry_watch_ok:
                    emit("watch_status=weekly_retry_nonzero_continue_to_conclusion_check", level="warning", flush=True)
                retry_conclusion = run_view_field(args.gh_path, args.repo, retry_weekly_run_id, "conclusion", retry_delays).lower()
                emit(f"weekly_retry_conclusion={retry_conclusion or 'unknown'}")
                if retry_conclusion == "success":
                    weekly_run_id = retry_weekly_run_id
                    conclusion = retry_conclusion
                    emit(f"weekly_recovered_by_retry_run_id={weekly_run_id}")
                else:
                    print_failure_hint(args.gh_path, args.repo, retry_weekly_run_id, retry_delays, label="weekly_retry")
                    raise RuntimeError(f"weekly benchmark retry did not succeed: {retry_weekly_run_id}")
            if conclusion != "success":
                raise RuntimeError(f"weekly benchmark run did not succeed: {weekly_run_id}")

        if args.skip_publish:
            emit("publish_skipped=true")
            return 0

        did_manual_publish = False
        if args.publish_mode in {"auto", "auto-then-manual"}:
            try:
                emit(f"phase=wait_auto_publish source_weekly_run_id={weekly_run_id}", flush=True)
                auto_publish_run_id = wait_auto_publish_workflow_run(
                    gh_path=args.gh_path,
                    repo=args.repo,
                    workflow=str(args.publish_workflow),
                    retry_delays=retry_delays,
                    poll_interval_s=int(args.poll_interval_s),
                    poll_timeout_s=int(args.poll_timeout_s),
                )
                emit(f"phase=watch_auto_publish run_id={auto_publish_run_id}", flush=True)
                auto_watch_ok = watch_run(args.gh_path, args.repo, auto_publish_run_id, retry_delays)
                if not auto_watch_ok:
                    emit("watch_status=auto_publish_nonzero_continue_to_conclusion_check", level="warning", flush=True)
                auto_conclusion = run_view_field(args.gh_path, args.repo, auto_publish_run_id, "conclusion", retry_delays).lower()
                emit(f"auto_publish_conclusion={auto_conclusion or 'unknown'}")
                if auto_conclusion == "success":
                    emit("phase=pipeline_completed", flush=True)
                    return 0
                print_failure_hint(args.gh_path, args.repo, auto_publish_run_id, retry_delays, label="auto_publish")
                if args.publish_mode == "auto":
                    raise RuntimeError(f"auto publish run did not succeed: {auto_publish_run_id}")
            except Exception as exc:  # noqa: BLE001
                emit(f"auto_publish_error={exc}", level="error")
                if args.publish_mode == "auto":
                    raise

        if args.publish_mode in {"manual", "auto-then-manual"}:
            emit(f"phase=dispatch_publish source_weekly_run_id={weekly_run_id}", flush=True)
            run_publish_wrapper(
                gh_path=args.gh_path,
                repo=args.repo,
                source_run_id=weekly_run_id,
                apply_retirement_candidates=args.apply_retirement_candidates,
                retirement_min_stale_runs=int(args.retirement_min_stale_runs),
                retirement_max_seen_ok_count=int(args.retirement_max_seen_ok_count),
                retry_delays_s=str(args.retry_delays_s),
            )
            did_manual_publish = True
        if not did_manual_publish and args.publish_mode not in {"auto", "auto-then-manual"}:
            raise RuntimeError(f"unsupported publish mode: {args.publish_mode}")
        emit("phase=pipeline_completed", flush=True)
        return 0
    except Exception as exc:
        emit(f"error={exc}", level="error", stderr=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
