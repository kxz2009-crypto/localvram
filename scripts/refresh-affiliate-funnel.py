#!/usr/bin/env python3
import argparse
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_SCRIPT = ROOT / "scripts" / "import-affiliate-events.py"
BUILD_SCRIPT = ROOT / "scripts" / "build-conversion-funnel.py"
QUALITY_GATE = ROOT / "scripts" / "quality-gate.py"


def run_cmd(cmd: list[str], cwd: Path) -> None:
    print(f"+ {shlex.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot affiliate funnel refresh: import events -> rebuild funnel -> validate -> optional commit/push."
    )
    parser.add_argument("--source-file", required=True, help="Raw affiliate export file (json/jsonl/ndjson)")
    parser.add_argument("--source-format", choices=["auto", "json", "jsonl"], default="auto")
    parser.add_argument("--source-label", default="cloudflare_kv_import")
    parser.add_argument("--max-age-days", type=int, default=45)
    parser.add_argument("--max-events", type=int, default=10000)
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument(
        "--affiliate-target-file",
        default=str(ROOT / "src" / "data" / "affiliate-click-events.json"),
        help="Target affiliate events JSON file path.",
    )
    parser.add_argument(
        "--funnel-output-file",
        default=str(ROOT / "src" / "data" / "conversion-funnel.json"),
        help="Output conversion funnel JSON file path.",
    )
    parser.add_argument(
        "--search-console-file",
        default=str(ROOT / "src" / "data" / "search-console-keywords.json"),
        help="Search Console keyword snapshot file path.",
    )
    parser.add_argument("--skip-quality-gate", action="store_true")
    parser.add_argument("--git-commit", action="store_true", help="Commit changed funnel data files.")
    parser.add_argument("--git-push", action="store_true", help="Push after commit (requires --git-commit).")
    parser.add_argument(
        "--commit-message",
        default="data: refresh affiliate events and conversion funnel",
        help="Git commit message when --git-commit is set.",
    )
    args = parser.parse_args()

    if args.git_push and not args.git_commit:
        raise SystemExit("--git-push requires --git-commit")

    source_file = Path(args.source_file)
    affiliate_target = Path(args.affiliate_target_file)
    funnel_output = Path(args.funnel_output_file)
    search_console_file = Path(args.search_console_file)

    run_cmd(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--source-file",
            str(source_file),
            "--target-file",
            str(affiliate_target),
            "--source-format",
            str(args.source_format),
            "--source-label",
            str(args.source_label),
            "--max-age-days",
            str(int(args.max_age_days)),
            "--max-events",
            str(int(args.max_events)),
        ],
        ROOT,
    )

    run_cmd(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--search-console-file",
            str(search_console_file),
            "--affiliate-events-file",
            str(affiliate_target),
            "--output-file",
            str(funnel_output),
            "--window-days",
            str(int(args.window_days)),
        ],
        ROOT,
    )

    if not args.skip_quality_gate:
        run_cmd([sys.executable, str(QUALITY_GATE)], ROOT)

    if args.git_commit:
        run_cmd(["git", "add", str(affiliate_target), str(funnel_output)], ROOT)
        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(ROOT),
            check=False,
        )
        if diff_check.returncode == 0:
            print("no staged changes for funnel data; skip commit")
        else:
            run_cmd(["git", "commit", "-m", str(args.commit_message)], ROOT)
            if args.git_push:
                run_cmd(["git", "push"], ROOT)

    print("refresh_affiliate_funnel=done")


if __name__ == "__main__":
    main()
