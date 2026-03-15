#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

from logging_utils import configure_logging


LOGGER = configure_logging("rewrite-cn-html-links")
ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rewrite CN html absolute links from .com to .cn.")
    parser.add_argument("--dist", default="dist-cn", help="CN artifact directory")
    parser.add_argument("--from-origin", default="https://localvram.com", help="Source origin")
    parser.add_argument("--to-origin", default="https://localvram.cn", help="Target origin")
    return parser.parse_args()


def normalize_origin(value: str) -> str:
    return str(value).strip().rstrip("/")


def rewrite_html_text(text: str, from_origin: str, to_origin: str) -> tuple[str, int]:
    # CN root-path strategy: rewrite root-relative /en/* links to /*.
    # Do not rewrite absolute .com URLs here, otherwise cross-domain hreflang
    # links (en/x-default -> .com) may be unintentionally rewritten to .cn.
    rewritten, first_hits = re.subn(r'(["\'])/en/', r"\1/", text)
    rewritten, second_hits = re.subn(r'(["\'])/en(?=(["\'#?]))', r"\1/", rewritten)
    return rewritten, first_hits + second_hits


def main() -> None:
    args = parse_args()
    dist_dir = (ROOT / args.dist).resolve()
    from_origin = normalize_origin(args.from_origin)
    to_origin = normalize_origin(args.to_origin)

    if not dist_dir.exists():
        LOGGER.error("dist directory missing: %s", dist_dir)
        sys.exit(1)

    changed_files = 0
    replacement_hits = 0
    for html_file in dist_dir.rglob("*.html"):
        original = html_file.read_text(encoding="utf-8")
        updated, hit_count = rewrite_html_text(original, from_origin, to_origin)
        if updated == original:
            continue
        replacement_hits += hit_count
        html_file.write_text(updated, encoding="utf-8")
        changed_files += 1

    LOGGER.info(
        "rewrote cn html links: changed_files=%s root_relative_rewrites=%s from=%s to=%s",
        changed_files,
        replacement_hits,
        from_origin,
        to_origin,
    )


if __name__ == "__main__":
    main()
