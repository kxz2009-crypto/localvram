#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"


def run_script(script_name: str, script_args: list[str], label: str) -> subprocess.CompletedProcess[str]:
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
    return proc


def run_cmd(cmd: list[str], label: str) -> subprocess.CompletedProcess[str]:
    print(f"== {label} ==")
    print("command=" + " ".join(shlex.quote(x) for x in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(ROOT))
    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        raise SystemExit(proc.returncode)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    return proc


def parse_updated_paths(stdout: str) -> list[str]:
    out: list[str] = []
    for raw in (stdout or "").splitlines():
        line = raw.strip()
        if not line.startswith("updated="):
            continue
        part = line[len("updated=") :]
        path_token = part.split(" ", 1)[0].strip()
        if not path_token:
            continue
        normalized = path_token.replace("\\", "/")
        if normalized not in out:
            out.append(normalized)
    return out


def has_pre_staged_changes() -> bool:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return bool(proc.stdout.strip())


def run_git_commit_flow(
    *,
    files_to_stage: list[str],
    commit_message: str,
    git_push: bool,
    allow_prestaged: bool,
) -> None:
    if not files_to_stage:
        print("git_commit_skipped=no-target-files")
        return
    if not allow_prestaged and has_pre_staged_changes():
        raise SystemExit("refusing to auto-commit: existing staged changes detected (use --allow-prestaged)")

    run_cmd(["git", "add", "--", *files_to_stage], "git-add-review-files")

    has_staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    if has_staged.returncode == 0:
        print("git_commit_skipped=no-staged-delta")
        return
    if has_staged.returncode not in {0, 1}:
        raise SystemExit(has_staged.returncode)

    run_cmd(["git", "commit", "-m", commit_message], "git-commit-review-files")
    if git_push:
        run_cmd(["git", "push"], "git-push-review-files")


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
    content.add_argument("--dry-run", action="store_true")
    content.add_argument("--git-commit", action="store_true")
    content.add_argument("--git-push", action="store_true")
    content.add_argument("--git-commit-message", default="")
    content.add_argument("--allow-prestaged", action="store_true")

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
    submission.add_argument("--dry-run", action="store_true")
    submission.add_argument("--git-commit", action="store_true")
    submission.add_argument("--git-push", action="store_true")
    submission.add_argument("--git-commit-message", default="")
    submission.add_argument("--allow-prestaged", action="store_true")

    return parser.parse_args()


def run_content(args: argparse.Namespace) -> None:
    if not str(args.drafts).strip() and not str(args.slugs).strip():
        raise SystemExit("content review needs at least one selector: --drafts or --slugs")
    if args.git_push and not args.git_commit:
        raise SystemExit("--git-push requires --git-commit")
    if args.dry_run and (args.git_commit or args.git_push):
        raise SystemExit("--dry-run cannot be combined with --git-commit/--git-push")

    cmd_args = ["--action", args.action, "--reviewer", args.reviewer]
    if str(args.queue_date).strip():
        cmd_args.extend(["--queue-date", str(args.queue_date).strip()])
    if str(args.drafts).strip():
        cmd_args.extend(["--drafts", str(args.drafts).strip()])
    if str(args.slugs).strip():
        cmd_args.extend(["--slugs", str(args.slugs).strip()])
    if str(args.note).strip():
        cmd_args.extend(["--note", str(args.note).strip()])
    if args.dry_run:
        cmd_args.append("--dry-run")

    result = run_script("review-content-drafts.py", cmd_args, "content-manual-review")
    changed_files = parse_updated_paths(result.stdout)

    if args.quality_gate:
        run_script("quality-gate.py", [], "quality-gate")

    if args.git_commit:
        queue_date = str(args.queue_date).strip() or "latest"
        default_message = f"chore: apply content review decisions ({args.action}) [{queue_date}]"
        run_git_commit_flow(
            files_to_stage=changed_files,
            commit_message=str(args.git_commit_message).strip() or default_message,
            git_push=bool(args.git_push),
            allow_prestaged=bool(args.allow_prestaged),
        )


def run_submission(args: argparse.Namespace) -> None:
    if args.git_push and not args.git_commit:
        raise SystemExit("--git-push requires --git-commit")
    if args.dry_run and (args.git_commit or args.git_push):
        raise SystemExit("--dry-run cannot be combined with --git-commit/--git-push")

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
    if args.dry_run:
        cmd_args.append("--dry-run")

    run_script("review-community-submissions.py", cmd_args, "submission-manual-review")
    changed_files = ["src/data/community-reports.json"]

    if not args.skip_snapshot_refresh and not args.dry_run:
        run_script("build-submission-review.py", [], "refresh-submission-snapshot")
        changed_files.append("src/data/submission-review.json")
    elif args.dry_run:
        print("dry_run_info=skip submission-review snapshot refresh in dry-run mode")

    if args.quality_gate:
        run_script("quality-gate.py", [], "quality-gate")

    if args.git_commit:
        default_message = f"chore: apply submission review decisions ({args.action})"
        run_git_commit_flow(
            files_to_stage=changed_files,
            commit_message=str(args.git_commit_message).strip() or default_message,
            git_push=bool(args.git_push),
            allow_prestaged=bool(args.allow_prestaged),
        )


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
