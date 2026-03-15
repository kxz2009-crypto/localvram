#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "src" / "content" / "blog"
I18N_BLOG_COPY_PATH = ROOT / "src" / "data" / "i18n-blog-copy.json"
STANDARD_I18N_LOCALES = ("es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id")
DEFAULT_CTA_LINE = "Start with a stable local baseline, then burst to cloud only for peak traffic."
FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(?P<frontmatter>[\s\S]*?)\r?\n---\s*(\r?\n)?")
LOGGER = configure_logging("sync-i18n-blog-copy")


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    return raw if isinstance(raw, dict) else default


def parse_frontmatter(markdown: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(markdown.lstrip("\ufeff"))
    if not match:
        return {}
    out: dict[str, str] = {}
    for raw in match.group("frontmatter").splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        text = value.strip().strip('"').strip("'")
        out[key.strip()] = text
    return out


def normalize_text(value: str) -> str:
    return str(value or "").strip()


def resolve_english_copy(frontmatter: dict[str, str], slug: str) -> dict[str, str]:
    title = normalize_text(frontmatter.get("title")) or slug.replace("-", " ").title()
    description = normalize_text(frontmatter.get("description")) or f"Practical local LLM guide: {title}."
    cta_line = DEFAULT_CTA_LINE
    return {"title": title, "description": description, "cta_line": cta_line}


def main() -> None:
    if not BLOG_DIR.exists():
        raise SystemExit(f"sync failed: missing blog directory: {BLOG_DIR}")

    payload = load_json(I18N_BLOG_COPY_PATH, {"updated_at": "", "wave": "auto-sync", "slugs": {}})
    slugs_payload = payload.get("slugs")
    if not isinstance(slugs_payload, dict):
        slugs_payload = {}

    created = 0
    hydrated = 0
    locale_filled = 0

    for blog_file in sorted(BLOG_DIR.glob("*.md")):
        slug = blog_file.stem
        frontmatter = parse_frontmatter(blog_file.read_text(encoding="utf-8"))
        english_defaults = resolve_english_copy(frontmatter, slug)

        entry = slugs_payload.get(slug)
        if not isinstance(entry, dict):
            entry = {}
            created += 1

        en_entry = entry.get("en")
        if not isinstance(en_entry, dict):
            en_entry = {}

        changed_en = False
        for field in ("title", "description", "cta_line"):
            value = normalize_text(en_entry.get(field))
            if not value:
                en_entry[field] = english_defaults[field]
                changed_en = True

        if changed_en:
            hydrated += 1

        locales_entry = entry.get("locales")
        if not isinstance(locales_entry, dict):
            locales_entry = {}

        for locale in STANDARD_I18N_LOCALES:
            locale_fields = locales_entry.get(locale)
            if not isinstance(locale_fields, dict):
                locale_fields = {}
            changed_locale = False
            for field in ("title", "description", "cta_line"):
                value = normalize_text(locale_fields.get(field))
                if not value:
                    locale_fields[field] = en_entry[field]
                    changed_locale = True
            if changed_locale:
                locale_filled += 1
            locales_entry[locale] = locale_fields

        entry["en"] = en_entry
        entry["locales"] = locales_entry
        slugs_payload[slug] = entry

    payload["slugs"] = slugs_payload
    payload["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if not normalize_text(payload.get("wave")):
        payload["wave"] = "auto-sync"

    I18N_BLOG_COPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    I18N_BLOG_COPY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    LOGGER.info(
        "sync complete: blog_slugs=%s created=%s hydrated_en=%s locale_entries_filled=%s file=%s",
        len(list(BLOG_DIR.glob("*.md"))),
        created,
        hydrated,
        locale_filled,
        I18N_BLOG_COPY_PATH,
    )


if __name__ == "__main__":
    main()
