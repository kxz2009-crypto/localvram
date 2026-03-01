#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COPY_FILE = ROOT / "src" / "data" / "i18n-copy.json"
OUT_FILE = ROOT / "dist" / "seo-audit" / "i18n-readiness.json"


def main() -> int:
    payload = json.loads(COPY_FILE.read_text(encoding="utf-8"))
    threshold = float(payload.get("fallback_noindex_threshold", 0.2))
    required_locales = [str(x).strip().lower() for x in payload.get("required_locales", []) if str(x).strip()]
    pages = payload.get("pages", {})

    summary: dict[str, dict[str, object]] = {}
    for locale in required_locales:
        page_rows = []
        ready = True
        for page_id, page_entry in pages.items():
            en_fields = page_entry.get("en", {}) if isinstance(page_entry, dict) else {}
            locale_fields = page_entry.get("locales", {}).get(locale, {}) if isinstance(page_entry, dict) else {}
            if not isinstance(en_fields, dict):
                continue
            keys = list(en_fields.keys())
            if not keys:
                ratio = 0.0
                fallback_fields = []
            else:
                fallback_fields = [
                    key
                    for key in keys
                    if not isinstance(locale_fields, dict)
                    or not isinstance(locale_fields.get(key), str)
                    or not str(locale_fields.get(key, "")).strip()
                ]
                ratio = len(fallback_fields) / len(keys)
            if ratio > threshold:
                ready = False
            page_rows.append(
                {
                    "page_id": page_id,
                    "fallback_ratio": round(ratio, 4),
                    "fallback_fields": fallback_fields,
                    "ready": ratio <= threshold,
                }
            )
        summary[locale] = {
            "ready": ready,
            "threshold": threshold,
            "pages": page_rows,
        }

    ready_locales = sorted([locale for locale, row in summary.items() if bool(row.get("ready"))])
    not_ready_locales = sorted([locale for locale, row in summary.items() if not bool(row.get("ready"))])
    report = {
        "threshold": threshold,
        "ready_locales": ready_locales,
        "not_ready_locales": not_ready_locales,
        "summary": summary,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"threshold={threshold}")
    print(f"ready_locales={','.join(ready_locales) if ready_locales else '(none)'}")
    print(f"not_ready_locales={','.join(not_ready_locales) if not_ready_locales else '(none)'}")
    print(f"report={OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
