#!/usr/bin/env python3
import json
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = ROOT / "dist" / "seo-audit" / "i18n-sitemap-section-report.json"
TARGET_LOCALES = ["es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id"]
KEY_SECTIONS = ["home", "tools", "errors", "status", "guides", "hardware", "models"]
LOGGER = configure_logging("check-i18n-section-parity")


def main() -> int:
    if not REPORT_FILE.exists():
        LOGGER.error("missing report file: %s", REPORT_FILE)
        return 1

    payload = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
    parity_map = checks.get("key_section_parity_ratio_vs_en", {}) if isinstance(checks, dict) else {}

    errors: list[str] = []
    for locale in TARGET_LOCALES:
        locale_map = parity_map.get(locale, {}) if isinstance(parity_map, dict) else {}
        if not isinstance(locale_map, dict):
            errors.append(f"{locale}: missing key section parity map")
            continue
        for section in KEY_SECTIONS:
            ratio = locale_map.get(section)
            if ratio is None:
                errors.append(f"{locale}:{section} parity is missing")
                continue
            try:
                value = float(ratio)
            except (TypeError, ValueError):
                errors.append(f"{locale}:{section} parity is not numeric ({ratio})")
                continue
            if abs(value - 1.0) > 1e-9:
                errors.append(f"{locale}:{section} parity={value} (expected 1.0)")

    if errors:
        LOGGER.error("key section parity check failed (%s issue(s))", len(errors))
        for item in errors:
            LOGGER.error("- %s", item)
        return 1

    LOGGER.info(
        "key section parity check passed: locales=%s sections=%s report=%s",
        len(TARGET_LOCALES),
        len(KEY_SECTIONS),
        REPORT_FILE,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
