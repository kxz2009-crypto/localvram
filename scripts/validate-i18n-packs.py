#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COPY_PATH = ROOT / "src" / "data" / "i18n-copy.json"
PACK_ROOT = ROOT / "src" / "data" / "i18n-packs"
REPORT_PATH = ROOT / "dist" / "seo-audit" / "i18n-pack-status.json"
STANDARD_I18N_LOCALES = {"es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"}
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z0-9_]+\}")


def extract_placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(text or ""))


def english_phrase_set(payload: dict) -> set[str]:
    phrases: set[str] = set()
    pages = payload.get("pages", {})
    if not isinstance(pages, dict):
        return phrases
    for page in pages.values():
        en_fields = page.get("en", {}) if isinstance(page, dict) else {}
        if not isinstance(en_fields, dict):
            continue
        for value in en_fields.values():
            phrases.add(str(value))
    return phrases


def fail(message: str) -> None:
    print(f"i18n pack validation failed: {message}")
    sys.exit(1)


def main() -> None:
    if not COPY_PATH.exists():
        fail(f"missing source file: {COPY_PATH}")

    payload = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    source_phrases = english_phrase_set(payload)
    if not source_phrases:
        fail("no english source phrases found in i18n-copy.json")

    report: dict = {
        "source_phrase_count": len(source_phrases),
        "packs": [],
    }

    if not PACK_ROOT.exists():
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("i18n pack validation ok: no pack directory present")
        return

    pack_files = sorted(PACK_ROOT.rglob("*.json"))
    if not pack_files:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("i18n pack validation ok: no pack files present")
        return

    for pack_file in pack_files:
        rel = pack_file.relative_to(ROOT)
        pack_data = json.loads(pack_file.read_text(encoding="utf-8"))

        locale = str(pack_data.get("locale", "")).strip().lower()
        if not locale:
            fail(f"{rel} missing locale")
        if locale not in STANDARD_I18N_LOCALES:
            fail(f"{rel} has unknown locale: {locale}")

        phrases = pack_data.get("phrases")
        if not isinstance(phrases, list):
            fail(f"{rel} phrases must be an array")

        seen_en: set[str] = set()
        filled = 0

        for idx, row in enumerate(phrases):
            if not isinstance(row, dict):
                fail(f"{rel} row[{idx}] must be an object")
            en = str(row.get("en", ""))
            tr = str(row.get("translation", ""))
            if not en:
                fail(f"{rel} row[{idx}] missing 'en'")
            if en in seen_en:
                fail(f"{rel} has duplicate source phrase: {en}")
            seen_en.add(en)
            if en not in source_phrases:
                fail(f"{rel} has unknown source phrase: {en}")

            if tr.strip():
                src_ph = extract_placeholders(en)
                dst_ph = extract_placeholders(tr)
                if src_ph != dst_ph:
                    fail(
                        f"{rel} placeholder mismatch for phrase '{en}': source={sorted(src_ph)} target={sorted(dst_ph)}"
                    )
                filled += 1

        missing_phrases = sorted(source_phrases - seen_en)
        if missing_phrases:
            fail(f"{rel} missing {len(missing_phrases)} source phrases")

        extra_phrases = sorted(seen_en - source_phrases)
        if extra_phrases:
            fail(f"{rel} contains unexpected source phrases")

        total = len(seen_en)
        ratio = (filled / total) if total else 0.0
        report["packs"].append(
            {
                "file": str(rel).replace("\\", "/"),
                "locale": locale,
                "filled": filled,
                "total": total,
                "ratio": round(ratio, 6),
            }
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"i18n pack validation ok: packs={len(report['packs'])} source_phrases={len(source_phrases)} report={REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
