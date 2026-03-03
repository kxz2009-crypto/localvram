#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "src" / "data" / "i18n-copy.json"
STANDARD_I18N_LOCALES = ("es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id")
LOGGER = configure_logging("export-i18n-translation-template")


def collect_unique_english_phrases(payload: dict) -> list[str]:
    phrases: set[str] = set()
    pages = payload.get("pages", {})
    if not isinstance(pages, dict):
        return []
    for page in pages.values():
        en_fields = page.get("en", {}) if isinstance(page, dict) else {}
        if not isinstance(en_fields, dict):
            continue
        for value in en_fields.values():
            phrases.add(str(value))
    return sorted(phrases)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export i18n translation template from i18n-copy english phrases.")
    parser.add_argument("--locale", help="Target locale, e.g. fr/de/ru.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export templates for all 10 standard locales.",
    )
    parser.add_argument(
        "--out",
        help="Output json file path. Default: dist/seo-audit/i18n-template-<locale>.json",
    )
    args = parser.parse_args()

    if args.all and args.out:
        raise SystemExit("invalid args: --out cannot be combined with --all")
    if not args.all and not args.locale:
        raise SystemExit("invalid args: provide --locale <code> or use --all")

    payload = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    phrases = collect_unique_english_phrases(payload)

    locales: list[str]
    if args.all:
        locales = list(STANDARD_I18N_LOCALES)
    else:
        locales = [str(args.locale).strip().lower()]

    for locale in locales:
        out_path = (
            Path(args.out)
            if args.out
            else ROOT / "dist" / "seo-audit" / f"i18n-template-{locale}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        template = {
            "locale": locale,
            "source_locale": "en",
            "phrases": [{"en": text, "translation": ""} for text in phrases],
        }
        out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        LOGGER.info("exported template: locale=%s phrases=%s file=%s", locale, len(phrases), out_path)


if __name__ == "__main__":
    main()
