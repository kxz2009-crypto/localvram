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
from typing import Iterable


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


def _parse_retry_delays(raw: str) -> list[int]:
    out: list[int] = []
    for piece in (raw or "").split(","):
        piece = piece.strip()
        if not piece:
            continue
        out.append(max(0, int(piece)))
    if not out:
        out = [5, 10, 20]
    return out


def _is_transient_error(stderr: str) -> bool:
    text = (stderr or "").lower()
    return any(pat in text for pat in TRANSIENT_ERROR_PATTERNS)


def _run_gh(
    gh_path: str,
    args: list[str],
    retry_delays: Iterable[int],
    allow_retry: bool = True,
) -> subprocess.CompletedProcess[str]:
    delays = list(retry_delays) if allow_retry else []
    attempt = 0
    cmd = [gh_path, *args]
    while True:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return proc
        if attempt >= len(delays) or not _is_transient_error(proc.stderr):
            return proc
        delay = delays[attempt]
        attempt += 1
        print(
            f"gh command failed ({proc.returncode}), retrying in {delay}s: {' '.join(args)}",
            file=sys.stderr,
        )
        time.sleep(delay)


def _gh_api_json(
    gh_path: str,
    endpoint: str,
    retry_delays: Iterable[int],
) -> dict:
    proc = _run_gh(gh_path, ["api", endpoint], retry_delays, allow_retry=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid gh api json for {endpoint}: {exc}") from exc


def _resolve_latest_successful_weekly_run_id(
    gh_path: str,
    repo: str,
    weekly_workflow: str,
    retry_delays: Iterable[int],
) -> int:
    endpoint = f"repos/{repo}/actions/workflows/{weekly_workflow}/runs?status=completed&per_page=30"
    data = _gh_api_json(gh_path, endpoint, retry_delays)
    runs = data.get("workflow_runs") or []
    for run in runs:
        if str(run.get("conclusion")) == "success":
            run_id = run.get("id")
            if isinstance(run_id, int):
                return run_id
    raise RuntimeError("no successful weekly workflow run found")


def _latest_publish_dispatch_run_id(
    gh_path: str,
    repo: str,
    publish_workflow: str,
    retry_delays: Iterable[int],
) -> int | None:
    endpoint = f"repos/{repo}/actions/workflows/{publish_workflow}/runs?event=workflow_dispatch&per_page=5"
    data = _gh_api_json(gh_path, endpoint, retry_delays)
    runs = data.get("workflow_runs") or []
    if not runs:
        return None
    run_id = runs[0].get("id")
    return run_id if isinstance(run_id, int) else None


def _find_new_publish_dispatch_run(
    gh_path: str,
    repo: str,
    publish_workflow: str,
    baseline_run_id: int | None,
    started_at_utc: datetime,
    retry_delays: Iterable[int],
    poll_interval_s: int,
    poll_timeout_s: int,
) -> tuple[int, str | None]:
    deadline = time.time() + max(5, poll_timeout_s)
    endpoint = f"repos/{repo}/actions/workflows/{publish_workflow}/runs?event=workflow_dispatch&per_page=10"
    while time.time() < deadline:
        data = _gh_api_json(gh_path, endpoint, retry_delays)
        runs = data.get("workflow_runs") or []
        for run in runs:
            run_id = run.get("id")
            if not isinstance(run_id, int):
                continue
            created_at_raw = str(run.get("created_at") or "")
            created_at = None
            if created_at_raw:
                try:
                    created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                except ValueError:
                    created_at = None
            if baseline_run_id is not None and run_id == baseline_run_id:
                continue
            if created_at is not None and created_at < started_at_utc:
                continue
            return run_id, run.get("html_url")
        time.sleep(max(1, poll_interval_s))
    raise RuntimeError("timed out waiting for the new publish workflow run to appear")


def _watch_run(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int]) -> None:
    proc = _run_gh(
        gh_path,
        ["run", "watch", str(run_id), "-R", repo, "--exit-status"],
        retry_delays,
        allow_retry=True,
    )
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "watch failed"
        raise RuntimeError(stderr)


def _print_run_summary(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int]) -> None:
    proc = _run_gh(
        gh_path,
        ["run", "view", str(run_id), "-R", repo, "--json", "conclusion,url,updatedAt,name"],
        retry_delays,
        allow_retry=True,
    )
    if proc.returncode != 0:
        print(f"run_id={run_id}")
        print("run_summary=unavailable")
        return
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        print(f"run_id={run_id}")
        print("run_summary=unavailable")
        return
    print(f"run_id={run_id}")
    print(f"run_name={payload.get('name') or 'unknown'}")
    print(f"run_conclusion={payload.get('conclusion') or 'unknown'}")
    print(f"run_url={payload.get('url') or ''}")
    print(f"run_updated_at={payload.get('updatedAt') or ''}")


def _assert_gh_auth(gh_path: str, retry_delays: Iterable[int]) -> None:
    proc = _run_gh(gh_path, ["auth", "status", "-h", "github.com"], retry_delays, allow_retry=True)
    if proc.returncode != 0:
        raise RuntimeError("gh auth is not ready; run 'gh auth login -h github.com -p https -w'")


def _parse_run_id_from_workflow_run_output(stdout: str) -> int | None:
    match = re.search(r"/actions/runs/(\d+)", stdout or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dispatch Publish Benchmark Artifact safely with retry and optional watch.",
    )
    parser.add_argument("--gh-path", default="gh")
    parser.add_argument("--repo", default=os.getenv("LV_GH_REPO", "kxz2009-crypto/localvram"))
    parser.add_argument("--publish-workflow", default="publish-benchmark-artifact.yml")
    parser.add_argument("--weekly-workflow", default="weekly-benchmark.yml")
    parser.add_argument("--source-run-id", type=int, default=0)
    parser.add_argument("--apply-retirement-candidates", choices=["true", "false"], default="false")
    parser.add_argument("--retirement-min-stale-runs", type=int, default=3)
    parser.add_argument("--retirement-max-seen-ok-count", type=int, default=2)
    parser.add_argument("--retry-delays-s", default=os.getenv("LV_NETWORK_RETRY_DELAYS_S", "5,10,20"))
    parser.add_argument("--poll-interval-s", type=int, default=5)
    parser.add_argument("--poll-timeout-s", type=int, default=120)
    parser.add_argument("--no-watch", action="store_true")
    args = parser.parse_args()

    retry_delays = _parse_retry_delays(args.retry_delays_s)
    started_at_utc = datetime.now(timezone.utc)

    try:
        _assert_gh_auth(args.gh_path, retry_delays)
        source_run_id = int(args.source_run_id or 0)
        if source_run_id <= 0:
            source_run_id = _resolve_latest_successful_weekly_run_id(
                args.gh_path,
                args.repo,
                args.weekly_workflow,
                retry_delays,
            )
            print(f"resolved_source_run_id={source_run_id}")
        else:
            print(f"source_run_id={source_run_id}")

        baseline_id = _latest_publish_dispatch_run_id(
            args.gh_path,
            args.repo,
            args.publish_workflow,
            retry_delays,
        )
        if baseline_id is not None:
            print(f"baseline_publish_run_id={baseline_id}")

        dispatch_args = [
            "workflow",
            "run",
            args.publish_workflow,
            "-R",
            args.repo,
            "-f",
            f"source_run_id={source_run_id}",
            "-f",
            f"apply_retirement_candidates={args.apply_retirement_candidates}",
            "-f",
            f"retirement_min_stale_runs={args.retirement_min_stale_runs}",
            "-f",
            f"retirement_max_seen_ok_count={args.retirement_max_seen_ok_count}",
        ]
        dispatch = _run_gh(args.gh_path, dispatch_args, retry_delays, allow_retry=True)
        if dispatch.returncode != 0:
            raise RuntimeError(dispatch.stderr.strip() or "workflow dispatch failed")
        if dispatch.stdout.strip():
            print(dispatch.stdout.strip())

        dispatched_id = _parse_run_id_from_workflow_run_output(dispatch.stdout)
        if dispatched_id is None:
            dispatched_id, run_url = _find_new_publish_dispatch_run(
                args.gh_path,
                args.repo,
                args.publish_workflow,
                baseline_id,
                started_at_utc,
                retry_delays,
                args.poll_interval_s,
                args.poll_timeout_s,
            )
            print(f"dispatched_publish_run_id={dispatched_id}")
            if run_url:
                print(f"dispatched_publish_run_url={run_url}")
        else:
            print(f"dispatched_publish_run_id={dispatched_id}")

        if not args.no_watch:
            _watch_run(args.gh_path, args.repo, dispatched_id, retry_delays)
        _print_run_summary(args.gh_path, args.repo, dispatched_id, retry_delays)
        return 0
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
