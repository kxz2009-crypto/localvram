#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

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
        print(f"gh command failed ({proc.returncode}), retrying in {delay}s: {' '.join(args)}", file=sys.stderr)
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


def latest_weekly_run_id(gh_path: str, repo: str, workflow: str, retry_delays: Iterable[int]) -> int | None:
    proc = run_gh(
        gh_path,
        ["api", f"repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=5", "--jq", ".workflow_runs[0].id"],
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


def find_new_weekly_run_id(
    gh_path: str,
    repo: str,
    workflow: str,
    baseline_id: int | None,
    started_at: datetime,
    retry_delays: Iterable[int],
    poll_interval_s: int,
    poll_timeout_s: int,
) -> int:
    deadline = time.time() + max(10, poll_timeout_s)
    while time.time() < deadline:
        proc = run_gh(
            gh_path,
            ["api", f"repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=10"],
            retry_delays,
            allow_retry=True,
        )
        if proc.returncode != 0:
            time.sleep(max(1, poll_interval_s))
            continue
        import json

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
    raise RuntimeError("timed out waiting for weekly benchmark run id")


def watch_run(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int]) -> None:
    proc = run_gh(gh_path, ["run", "watch", str(run_id), "-R", repo, "--exit-status"], retry_delays, allow_retry=True)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"run watch failed for {run_id}")


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
    baseline = latest_weekly_run_id(gh_path, repo, workflow, retry_delays)
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
        print(proc.stdout.strip())

    run_id = parse_run_id_from_stdout(proc.stdout)
    if run_id is None:
        run_id = find_new_weekly_run_id(
            gh_path=gh_path,
            repo=repo,
            workflow=workflow,
            baseline_id=baseline,
            started_at=started_at,
            retry_delays=retry_delays,
            poll_interval_s=poll_interval_s,
            poll_timeout_s=poll_timeout_s,
        )
    print(f"weekly_run_id={run_id}")
    print(f"weekly_run_url=https://github.com/{repo}/actions/runs/{run_id}")
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
    print("dispatch_publish_command=" + " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise RuntimeError("publish wrapper failed")


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    retry_delays = parse_retry_delays(args.retry_delays_s)
    try:
        assert_gh_auth(args.gh_path, retry_delays)
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
        watch_run(args.gh_path, args.repo, weekly_run_id, retry_delays)
        conclusion = run_view_field(args.gh_path, args.repo, weekly_run_id, "conclusion", retry_delays).lower()
        print(f"weekly_conclusion={conclusion or 'unknown'}")
        if conclusion != "success":
            raise RuntimeError(f"weekly benchmark run did not succeed: {weekly_run_id}")

        if args.skip_publish:
            print("publish_skipped=true")
            return 0

        run_publish_wrapper(
            gh_path=args.gh_path,
            repo=args.repo,
            source_run_id=weekly_run_id,
            apply_retirement_candidates=args.apply_retirement_candidates,
            retirement_min_stale_runs=int(args.retirement_min_stale_runs),
            retirement_max_seen_ok_count=int(args.retirement_max_seen_ok_count),
            retry_delays_s=str(args.retry_delays_s),
        )
        return 0
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
