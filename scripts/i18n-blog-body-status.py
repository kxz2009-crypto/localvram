#!/usr/bin/env python3
import json
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
BLOG_DIR = ROOT / "src" / "content" / "blog"
BLOG_I18N_DIR = ROOT / "src" / "content" / "blog-i18n"
OUT_PATH = ROOT / "dist" / "seo-audit" / "i18n-blog-body-status.json"
STANDARD_I18N_LOCALES = ("es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id", "zh")
STUB_MARKERS = (
    "status: zh-stub",
    "pending full translation",
    "（中文整理中）",
    "## 英文摘要（原文引用）",
    "## 中文速览（待人工校对）",
)
LOGGER = configure_logging("i18n-blog-body-status")


def main() -> None:
    blog_slugs = sorted(p.stem for p in BLOG_DIR.glob("*.md"))
    total_slugs = len(blog_slugs)
    if total_slugs == 0:
        raise SystemExit("status failed: no source blog markdown files found")

    by_locale: dict[str, dict] = {}
    for locale in STANDARD_I18N_LOCALES:
        locale_dir = BLOG_I18N_DIR / locale
        localized_slugs = set()
        stub_slugs = set()
        if locale_dir.exists():
            for p in locale_dir.glob("*.md"):
                if p.stem not in blog_slugs:
                    continue
                content = p.read_text(encoding="utf-8")
                if not content.strip():
                    continue
                lowered = content.lower()
                is_stub = any(marker.lower() in lowered for marker in STUB_MARKERS)
                if is_stub:
                    stub_slugs.add(p.stem)
                    continue
                localized_slugs.add(p.stem)
        missing = [slug for slug in blog_slugs if slug not in localized_slugs]
        by_locale[locale] = {
            "localized": len(localized_slugs),
            "stub": len(stub_slugs),
            "total": total_slugs,
            "coverage": round(len(localized_slugs) / total_slugs, 4),
            "missing": missing,
            "stub_slugs": sorted(stub_slugs),
        }
        LOGGER.info(
            "locale=%s localized=%s/%s stub=%s coverage=%.4f",
            locale,
            len(localized_slugs),
            total_slugs,
            len(stub_slugs),
            len(localized_slugs) / total_slugs,
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "source_slugs": total_slugs,
                "locales": by_locale,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    LOGGER.info("report=%s", OUT_PATH)


if __name__ == "__main__":
    main()
