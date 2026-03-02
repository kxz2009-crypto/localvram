#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "src" / "data" / "i18n-copy.json"


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
    parser.add_argument("--locale", required=True, help="Target locale, e.g. fr/de/ru.")
    parser.add_argument(
        "--out",
        help="Output json file path. Default: dist/seo-audit/i18n-template-<locale>.json",
    )
    args = parser.parse_args()

    locale = str(args.locale).strip().lower()
    out_path = (
        Path(args.out)
        if args.out
        else ROOT / "dist" / "seo-audit" / f"i18n-template-{locale}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    phrases = collect_unique_english_phrases(payload)

    template = {
        "locale": locale,
        "source_locale": "en",
        "phrases": [{"en": text, "translation": ""} for text in phrases],
    }
    out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exported template: locale={locale} phrases={len(phrases)} file={out_path}")


if __name__ == "__main__":
    main()
