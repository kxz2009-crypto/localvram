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

from logging_utils import configure_logging


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
LOGGER = configure_logging("run-daily-content-workflow")


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
    cmd = [gh_path, *args]
    retries = list(retry_delays) if allow_retry else []
    attempt = 0
    while True:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return proc
        if attempt >= len(retries) or not is_transient_error(proc.stderr):
            return proc
        wait_s = retries[attempt]
        attempt += 1
        emit(
            f"gh command failed ({proc.returncode}), retrying in {wait_s}s: {' '.join(args)}",
            level="warning",
            stderr=True,
        )
        time.sleep(wait_s)


def assert_auth(gh_path: str, retry_delays: Iterable[int]) -> None:
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


def latest_dispatch_run_id(gh_path: str, repo: str, workflow: str, retry_delays: Iterable[int]) -> int | None:
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


def find_new_dispatch_run_id(
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
        try:
            payload = json.loads(proc.stdout or "{}")
        except Exception:  # noqa: BLE001
            payload = {}
        runs = payload.get("workflow_runs") or []
        for run in runs:
            run_id = run.get("id")
            if not isinstance(run_id, int):
                continue
            if baseline_id is not None and run_id == baseline_id:
                continue
            created_at_raw = str(run.get("created_at") or "")
            try:
                created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            except ValueError:
                created_at = None
            if created_at is not None and created_at < started_at:
                continue
            return run_id
        time.sleep(max(1, poll_interval_s))
    raise RuntimeError("timed out waiting for daily content run id")


def watch_run(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int]) -> None:
    proc = run_gh(gh_path, ["run", "watch", str(run_id), "-R", repo, "--exit-status"], retry_delays, allow_retry=True)
    if proc.stdout.strip():
        emit(proc.stdout.strip())
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"run watch failed: {run_id}")


def show_summary(gh_path: str, repo: str, run_id: int, retry_delays: Iterable[int]) -> None:
    proc = run_gh(
        gh_path,
        ["run", "view", str(run_id), "-R", repo, "--json", "conclusion,url,updatedAt,name"],
        retry_delays,
        allow_retry=True,
    )
    if proc.returncode != 0:
        emit(f"run_id={run_id}")
        emit("run_summary=unavailable")
        return
    try:
        payload = json.loads(proc.stdout or "{}")
    except Exception:  # noqa: BLE001
        emit(f"run_id={run_id}")
        emit("run_summary=unavailable")
        return
    emit(f"run_id={run_id}")
    emit(f"run_name={payload.get('name') or 'unknown'}")
    emit(f"run_conclusion={payload.get('conclusion') or 'unknown'}")
    emit(f"run_url={payload.get('url') or ''}")
    emit(f"run_updated_at={payload.get('updatedAt') or ''}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dispatch Daily Content Agent workflow and wait for completion.")
    parser.add_argument("--gh-path", default="gh")
    parser.add_argument("--repo", default=os.getenv("LV_GH_REPO", "kxz2009-crypto/localvram"))
    parser.add_argument("--workflow", default="daily-content.yml")
    parser.add_argument("--retry-delays-s", default=os.getenv("LV_NETWORK_RETRY_DELAYS_S", "5,10,20"))
    parser.add_argument("--poll-interval-s", type=int, default=5)
    parser.add_argument("--poll-timeout-s", type=int, default=120)
    parser.add_argument("--no-watch", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    retry_delays = parse_retry_delays(args.retry_delays_s)
    try:
        assert_auth(args.gh_path, retry_delays)
        baseline = latest_dispatch_run_id(args.gh_path, args.repo, args.workflow, retry_delays)
        started_at = datetime.now(timezone.utc)

        proc = run_gh(args.gh_path, ["workflow", "run", args.workflow, "-R", args.repo], retry_delays, allow_retry=True)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "failed to dispatch daily workflow")
        if proc.stdout.strip():
            emit(proc.stdout.strip())

        run_id = parse_run_id_from_stdout(proc.stdout)
        if run_id is None:
            run_id = find_new_dispatch_run_id(
                gh_path=args.gh_path,
                repo=args.repo,
                workflow=args.workflow,
                baseline_id=baseline,
                started_at=started_at,
                retry_delays=retry_delays,
                poll_interval_s=int(args.poll_interval_s),
                poll_timeout_s=int(args.poll_timeout_s),
            )

        emit(f"daily_run_id={run_id}")
        emit(f"daily_run_url=https://github.com/{args.repo}/actions/runs/{run_id}")

        if not args.no_watch:
            watch_run(args.gh_path, args.repo, run_id, retry_delays)

        show_summary(args.gh_path, args.repo, run_id, retry_delays)
        return 0
    except Exception as exc:
        emit(f"error={exc}", level="error", stderr=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
