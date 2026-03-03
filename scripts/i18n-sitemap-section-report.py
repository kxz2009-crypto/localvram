#!/usr/bin/env python3
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
OUT_FILE = ROOT / "dist" / "seo-audit" / "i18n-sitemap-section-report.json"
LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
LOCALE_RE = re.compile(r"^/([a-z]{2})(?:/|$)")
TARGET_LOCALES = ["en", "es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"]
LOGGER = configure_logging("i18n-sitemap-section-report")


def parse_sitemap_urls(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [m.group(1).strip() for m in LOC_RE.finditer(text)]


def classify_section(path: str) -> str:
    # path format: /{locale}/...
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return "home"
    section = parts[1]
    if section in {
        "guides",
        "status",
        "tools",
        "errors",
        "models",
        "blog",
        "hardware",
        "benchmarks",
        "about",
        "affiliate",
        "compare",
        "matrix",
        "multimodal",
        "updates",
    }:
        return section
    return "other"


def is_blog_detail(path: str) -> bool:
    # /{locale}/blog/{slug}/
    parts = [p for p in path.split("/") if p]
    return len(parts) >= 3 and parts[1] == "blog"


def main() -> int:
    report: dict[str, object] = {
        "locales": {},
        "checks": {},
    }
    locale_sections: dict[str, dict[str, int]] = {}
    blog_detail_counts: dict[str, int] = {}

    for locale in TARGET_LOCALES:
        sitemap_file = PUBLIC_DIR / f"sitemap-{locale}.xml"
        if not sitemap_file.exists():
            raise FileNotFoundError(f"missing sitemap file: {sitemap_file}")

        urls = parse_sitemap_urls(sitemap_file)
        sections: dict[str, int] = defaultdict(int)
        blog_detail = 0

        for url in urls:
            path = urlparse(url).path
            match = LOCALE_RE.match(path)
            if not match:
                continue
            detected_locale = match.group(1)
            if detected_locale != locale:
                continue
            section = classify_section(path)
            sections[section] += 1
            if is_blog_detail(path):
                blog_detail += 1

        locale_sections[locale] = dict(sorted(sections.items()))
        blog_detail_counts[locale] = blog_detail

    en_blog_details = blog_detail_counts.get("en", 0)
    blog_parity_ratio = {}
    for locale in TARGET_LOCALES:
        if locale == "en":
            continue
        if en_blog_details <= 0:
            blog_parity_ratio[locale] = None
        else:
            blog_parity_ratio[locale] = round(blog_detail_counts[locale] / en_blog_details, 4)

    report["locales"] = {
        locale: {
            "total_urls": sum(locale_sections[locale].values()),
            "sections": locale_sections[locale],
            "blog_detail_urls": blog_detail_counts[locale],
        }
        for locale in TARGET_LOCALES
    }
    report["checks"] = {
        "en_blog_detail_urls": en_blog_details,
        "blog_parity_ratio_vs_en": blog_parity_ratio,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    LOGGER.info("report=%s", OUT_FILE)
    LOGGER.info("en_blog_detail_urls=%s", en_blog_details)
    for locale in TARGET_LOCALES:
        if locale == "en":
            continue
        LOGGER.info(
            f"{locale}: total={sum(locale_sections[locale].values())} "
            f"blog_detail={blog_detail_counts[locale]} "
            f"parity={blog_parity_ratio[locale]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
