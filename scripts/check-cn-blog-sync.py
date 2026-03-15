#!/usr/bin/env python3
import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "src" / "content" / "blog"
CN_BLOG_DIR = ROOT / "src" / "content" / "blog-i18n" / "zh"
FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(?P<frontmatter>[\s\S]*?)\r?\n---\s*(\r?\n)?")
PUB_DATE_RE = re.compile(r"(?m)^pubDate:\s*(?P<value>.+?)\s*$")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ZH_STUB_MARKERS = (
    "status: zh-stub",
    "pending full translation",
    "（中文整理中）",
    "## 英文摘要（原文引用）",
    "## 中文速览（待人工校对）",
)
LOGGER = configure_logging("check-cn-blog-sync")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enforce CN zh blog sync for newly published EN posts.")
    parser.add_argument(
        "--since-date",
        default=str(os.environ.get("CN_BLOG_SYNC_SINCE", "")).strip(),
        help="Only enforce posts with pubDate >= YYYY-MM-DD. Defaults to CN_BLOG_SYNC_SINCE, otherwise UTC today.",
    )
    parser.add_argument(
        "--min-cjk-chars",
        type=int,
        default=12,
        help="Minimum count of CJK characters required in each zh translation file body.",
    )
    return parser.parse_args()


def parse_iso_date(raw: str) -> datetime.date:
    value = str(raw or "").strip().strip('"').strip("'")
    if not value:
        raise ValueError("empty date")
    if "T" in value:
        value = value.split("T", 1)[0]
    if " " in value:
        value = value.split(" ", 1)[0]
    if len(value) >= 10:
        value = value[:10]
    return datetime.strptime(value, "%Y-%m-%d").date()


def resolve_since_date(raw: str) -> datetime.date:
    if raw:
        return parse_iso_date(raw)
    return datetime.now(timezone.utc).date()


def read_frontmatter(markdown: str) -> str:
    normalized = markdown.lstrip("\ufeff")
    match = FRONTMATTER_RE.match(normalized)
    if not match:
        return ""
    return match.group("frontmatter")


def extract_pub_date(slug: str, markdown: str) -> datetime.date:
    frontmatter = read_frontmatter(markdown)
    if not frontmatter:
        raise ValueError(f"missing frontmatter in EN blog: {slug}")
    match = PUB_DATE_RE.search(frontmatter)
    if not match:
        raise ValueError(f"missing pubDate in EN blog: {slug}")
    return parse_iso_date(match.group("value"))


def strip_translation_markdown(markdown: str) -> str:
    text = markdown.lstrip()
    if text.startswith("<!--"):
        end = text.find("-->")
        if end >= 0:
            text = text[end + 3 :].lstrip()
    match = FRONTMATTER_RE.match(text)
    if match:
        text = text[match.end() :].lstrip()
    return text.strip()


def collect_en_posts(since_date: datetime.date) -> list[tuple[str, datetime.date]]:
    posts: list[tuple[str, datetime.date]] = []
    for file_path in sorted(BLOG_DIR.glob("*.md")):
        slug = file_path.stem
        markdown = file_path.read_text(encoding="utf-8")
        pub_date = extract_pub_date(slug, markdown)
        if pub_date >= since_date:
            posts.append((slug, pub_date))
    return posts


def validate_cn_translation(slug: str, min_cjk_chars: int) -> str | None:
    zh_file = CN_BLOG_DIR / f"{slug}.md"
    if not zh_file.exists():
        return f"missing zh translation file: {zh_file}"

    markdown = zh_file.read_text(encoding="utf-8")
    lower_markdown = markdown.lower()
    for marker in ZH_STUB_MARKERS:
        if marker.lower() in lower_markdown:
            return f"zh translation is still a stub placeholder: {zh_file} (marker={marker})"

    body = strip_translation_markdown(markdown)
    if not body:
        return f"empty zh translation body: {zh_file}"

    cjk_count = len(CJK_RE.findall(body))
    if cjk_count < min_cjk_chars:
        return (
            f"zh translation seems not localized enough: {zh_file} "
            f"(cjk_chars={cjk_count}, required>={min_cjk_chars})"
        )
    return None


def main() -> None:
    args = parse_args()
    since_date = resolve_since_date(args.since_date)
    LOGGER.info("cn blog sync enforcement date: %s", since_date.isoformat())

    if not BLOG_DIR.exists():
        raise SystemExit(f"sync check failed: missing EN blog directory: {BLOG_DIR}")

    target_posts = collect_en_posts(since_date)
    if not target_posts:
        LOGGER.info("cn blog sync ok: no EN posts on/after %s", since_date.isoformat())
        return

    errors: list[str] = []
    for slug, pub_date in target_posts:
        issue = validate_cn_translation(slug, args.min_cjk_chars)
        if issue:
            errors.append(f"{issue} (slug={slug}, pubDate={pub_date.isoformat()})")

    if errors:
        LOGGER.error("cn blog sync failed: checked=%s errors=%s", len(target_posts), len(errors))
        for issue in errors:
            LOGGER.error("- %s", issue)
        raise SystemExit(1)

    LOGGER.info(
        "cn blog sync ok: checked=%s since=%s zh_dir=%s",
        len(target_posts),
        since_date.isoformat(),
        CN_BLOG_DIR,
    )


if __name__ == "__main__":
    main()
