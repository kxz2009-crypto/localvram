#!/usr/bin/env python3
import json
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = ROOT / "dist" / "seo-audit" / "i18n-sitemap-section-report.json"
OUT_FILE = ROOT / "dist" / "seo-audit" / "i18n-section-parity-summary.json"
TARGET_LOCALES = ["es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"]
KEY_SECTIONS = ["home", "tools", "errors", "status", "guides", "hardware", "models"]
LOGGER = configure_logging("export-i18n-section-parity-summary")


def _to_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    if not REPORT_FILE.exists():
        LOGGER.error("missing report file: %s", REPORT_FILE)
        return 1

    payload = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    locales = payload.get("locales", {}) if isinstance(payload, dict) else {}
    checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
    parity_map = checks.get("key_section_parity_ratio_vs_en", {}) if isinstance(checks, dict) else {}

    en_sections_raw = (
        locales.get("en", {}).get("sections", {}) if isinstance(locales, dict) else {}
    )
    en_section_baseline = {
        section: int(en_sections_raw.get(section, 0) or 0) for section in KEY_SECTIONS
    }

    locale_section_counts: dict[str, dict[str, int]] = {}
    locale_section_parity: dict[str, dict[str, float | None]] = {}
    mismatches: list[dict[str, object]] = []

    for locale in TARGET_LOCALES:
        locale_sections_raw = (
            locales.get(locale, {}).get("sections", {}) if isinstance(locales, dict) else {}
        )
        locale_section_counts[locale] = {
            section: int(locale_sections_raw.get(section, 0) or 0) for section in KEY_SECTIONS
        }

        locale_map = parity_map.get(locale, {}) if isinstance(parity_map, dict) else {}
        locale_section_parity[locale] = {}
        for section in KEY_SECTIONS:
            ratio = _to_float(locale_map.get(section))
            locale_section_parity[locale][section] = ratio
            if ratio is None:
                mismatches.append(
                    {"locale": locale, "section": section, "reason": "missing_or_not_numeric", "ratio": None}
                )
                continue
            if abs(ratio - 1.0) > 1e-9:
                mismatches.append(
                    {"locale": locale, "section": section, "reason": "not_equal_1", "ratio": ratio}
                )

    summary = {
        "target_locales": TARGET_LOCALES,
        "key_sections": KEY_SECTIONS,
        "en_section_baseline": en_section_baseline,
        "locale_section_counts": locale_section_counts,
        "locale_section_parity": locale_section_parity,
        "counts": {
            "locale_count": len(TARGET_LOCALES),
            "section_count": len(KEY_SECTIONS),
            "cell_count": len(TARGET_LOCALES) * len(KEY_SECTIONS),
            "mismatch_count": len(mismatches),
        },
        "all_parity_exact": len(mismatches) == 0,
        "mismatches": mismatches,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info(
        "section parity summary generated: file=%s mismatch_count=%s",
        OUT_FILE,
        len(mismatches),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
