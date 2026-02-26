#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


def run_script(script_name: str, script_args: list[str], label: str) -> None:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise SystemExit(f"missing script: {script_path}")

    cmd = [sys.executable, str(script_path), *script_args]
    print(f"== {label} ==")
    print("command=" + " ".join(shlex.quote(x) for x in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.returncode != 0:
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        raise SystemExit(proc.returncode)
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified ops entry for manual review actions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    content = subparsers.add_parser("content", help="Review content queue drafts (manual action).")
    content.add_argument("--queue-date", default="")
    content.add_argument("--drafts", default="", help="Comma-separated draft filenames or relative paths.")
    content.add_argument("--slugs", default="", help="Comma-separated candidate slugs.")
    content.add_argument("--action", required=True, choices=["approve", "reject", "needs_info"])
    content.add_argument("--reviewer", default="ops")
    content.add_argument("--note", default="")
    content.add_argument("--quality-gate", action="store_true")

    submission = subparsers.add_parser("submission", help="Review queued community submissions.")
    submission.add_argument("--submission-ids", required=True, help="CSV submission ids.")
    submission.add_argument("--action", required=True, choices=["approve", "reject", "needs_info"])
    submission.add_argument("--reviewer", default="ops")
    submission.add_argument("--note", default="")
    submission.add_argument("--allow-non-pending", action="store_true")
    submission.add_argument(
        "--skip-snapshot-refresh",
        action="store_true",
        help="Skip rebuilding submission snapshot after review.",
    )
    submission.add_argument("--quality-gate", action="store_true")

    return parser.parse_args()


def run_content(args: argparse.Namespace) -> None:
    if not str(args.drafts).strip() and not str(args.slugs).strip():
        raise SystemExit("content review needs at least one selector: --drafts or --slugs")

    cmd_args = ["--action", args.action, "--reviewer", args.reviewer]
    if str(args.queue_date).strip():
        cmd_args.extend(["--queue-date", str(args.queue_date).strip()])
    if str(args.drafts).strip():
        cmd_args.extend(["--drafts", str(args.drafts).strip()])
    if str(args.slugs).strip():
        cmd_args.extend(["--slugs", str(args.slugs).strip()])
    if str(args.note).strip():
        cmd_args.extend(["--note", str(args.note).strip()])

    run_script("review-content-drafts.py", cmd_args, "content-manual-review")

    if args.quality_gate:
        run_script("quality-gate.py", [], "quality-gate")


def run_submission(args: argparse.Namespace) -> None:
    cmd_args = [
        "--submission-ids",
        str(args.submission_ids).strip(),
        "--action",
        args.action,
        "--reviewer",
        args.reviewer,
    ]
    if str(args.note).strip():
        cmd_args.extend(["--notes", str(args.note).strip()])
    if args.allow_non_pending:
        cmd_args.append("--allow-non-pending")

    run_script("review-community-submissions.py", cmd_args, "submission-manual-review")

    if not args.skip_snapshot_refresh:
        run_script("build-submission-review.py", [], "refresh-submission-snapshot")

    if args.quality_gate:
        run_script("quality-gate.py", [], "quality-gate")


def main() -> None:
    args = parse_args()
    if args.command == "content":
        run_content(args)
        return
    if args.command == "submission":
        run_submission(args)
        return
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
