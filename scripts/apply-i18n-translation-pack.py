#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "src" / "data" / "i18n-copy.json"

PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")


def extract_placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(text or ""))


def load_phrase_map(pack_data: dict) -> dict[str, str]:
    # Supports:
    # 1) {"translations": {"en text": "translated text"}}
    # 2) {"phrases": [{"en": "...", "translation": "..."}]}
    if isinstance(pack_data.get("translations"), dict):
        return {str(k): str(v) for k, v in pack_data["translations"].items()}

    phrases = pack_data.get("phrases")
    if not isinstance(phrases, list):
        raise ValueError("pack must contain either 'translations' map or 'phrases' array")
    result: dict[str, str] = {}
    for row in phrases:
        if not isinstance(row, dict):
            continue
        en = str(row.get("en", ""))
        tr = str(row.get("translation", ""))
        if en:
            result[en] = tr
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply translation pack to i18n-copy locale fields.")
    parser.add_argument("--locale", required=True, help="Target locale, e.g. fr/de/ru.")
    parser.add_argument("--pack", required=True, help="Translation pack json path.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any english phrase is missing/empty in pack.",
    )
    args = parser.parse_args()

    locale = str(args.locale).strip().lower()
    pack_path = Path(args.pack)
    if not pack_path.exists():
        print(f"apply failed: pack file not found: {pack_path}")
        sys.exit(1)

    payload = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    pages = payload.get("pages", {})
    if not isinstance(pages, dict):
        print("apply failed: i18n-copy pages must be an object")
        sys.exit(1)

    pack_data = json.loads(pack_path.read_text(encoding="utf-8"))
    phrase_map = load_phrase_map(pack_data)

    missing: set[str] = set()
    placeholder_errors: list[str] = []
    updated_fields = 0

    for page_id, page in pages.items():
        if not isinstance(page, dict):
            continue
        en_fields = page.get("en", {})
        locales = page.get("locales", {})
        if not isinstance(en_fields, dict) or not isinstance(locales, dict):
            continue

        locale_fields = locales.get(locale, {})
        if not isinstance(locale_fields, dict):
            locale_fields = {}

        for field_name, en_value in en_fields.items():
            en_text = str(en_value)
            translated = phrase_map.get(en_text, "")
            if args.strict and not translated.strip():
                missing.add(en_text)
                continue
            if not translated.strip():
                continue

            src_ph = extract_placeholders(en_text)
            dst_ph = extract_placeholders(translated)
            if src_ph != dst_ph:
                placeholder_errors.append(
                    f"page={page_id} field={field_name} source={sorted(src_ph)} target={sorted(dst_ph)} text={en_text}"
                )
                continue

            locale_fields[field_name] = translated
            updated_fields += 1

        locales[locale] = locale_fields
        page["locales"] = locales
        pages[page_id] = page

    if missing:
        print("apply failed: translation pack missing required phrases")
        for text in sorted(missing):
            print(f"- {text}")
        sys.exit(1)

    if placeholder_errors:
        print("apply failed: placeholder mismatch found")
        for row in placeholder_errors[:80]:
            print(f"- {row}")
        if len(placeholder_errors) > 80:
            print(f"- ... and {len(placeholder_errors) - 80} more")
        sys.exit(1)

    payload["pages"] = pages
    COPY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied locale={locale} updated_fields={updated_fields} source_pack={pack_path}")


if __name__ == "__main__":
    main()
