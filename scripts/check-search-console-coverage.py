#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
LOCALE_RE = re.compile(r"^[a-z]{2}$")


def parse_locales(raw: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for chunk in str(raw or "").split(","):
        locale = chunk.strip().lower()
        if not locale or locale in seen:
            continue
        if not LOCALE_RE.fullmatch(locale):
            continue
        seen.add(locale)
        out.append(locale)
    return out


def parse_iso_utc(value: str) -> dt.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def locale_from_item(item: dict) -> str:
    locale = str(item.get("locale", "")).strip().lower()
    if LOCALE_RE.fullmatch(locale):
        return locale
    landing = str(item.get("landing", "")).strip()
    m = re.match(r"^/([a-z]{2})(/|$)", landing)
    if not m:
        return ""
    return m.group(1).lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Search Console snapshot coverage for locale KPI refresh.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to search-console-keywords.json")
    parser.add_argument("--locales", default="en", help="Required locales CSV")
    parser.add_argument("--max-age-hours", type=int, default=96, help="Maximum allowed data age")
    parser.add_argument("--min-items-per-locale", type=int, default=1, help="Minimum keyword rows per locale")
    parser.add_argument("--expected-source", default="google-search-console-api", help="Expected snapshot source")
    parser.add_argument("--allow-stub-data", choices=["true", "false"], default="false")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = (ROOT / file_path).resolve()

    required_locales = parse_locales(args.locales)
    if not required_locales:
        print("gsc_coverage_error=no_valid_locales")
        return 1

    if not file_path.exists():
        print(f"gsc_coverage_error=missing_file path={file_path}")
        return 1

    payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
    items = payload.get("items", []) if isinstance(payload, dict) else []
    source = str(payload.get("source", "")).strip()
    updated_at_raw = str(payload.get("updated_at", "")).strip()
    updated_at = parse_iso_utc(updated_at_raw)

    counts: dict[str, int] = {locale: 0 for locale in required_locales}
    for row in items:
        if not isinstance(row, dict):
            continue
        locale = locale_from_item(row)
        if locale not in counts:
            continue
        counts[locale] += 1

    stale = True
    age_hours = -1.0
    if updated_at is not None:
        age = dt.datetime.now(dt.timezone.utc) - updated_at
        age_hours = round(age.total_seconds() / 3600, 2)
        stale = age.total_seconds() > max(0, int(args.max_age_hours)) * 3600

    missing_locales = sorted(
        [locale for locale, count in counts.items() if count < max(0, int(args.min_items_per_locale))]
    )
    allow_stub = str(args.allow_stub_data).strip().lower() == "true"
    source_ok = source == str(args.expected_source).strip()

    print(f"gsc_file={file_path}")
    print(f"gsc_updated_at={updated_at_raw or 'unknown'}")
    print(f"gsc_age_hours={age_hours}")
    print(f"gsc_source={source or 'unknown'}")
    print("gsc_locale_counts=" + ",".join([f"{locale}:{counts.get(locale, 0)}" for locale in required_locales]))

    errors: list[str] = []
    if stale:
        errors.append(f"stale_data(max_age_hours={args.max_age_hours})")
    if not source_ok and not allow_stub:
        errors.append(f"unexpected_source(expected={args.expected_source}, got={source or 'unknown'})")
    if missing_locales:
        errors.append("missing_locales=" + ",".join(missing_locales))

    if errors:
        print("gsc_coverage_result=failed")
        for error in errors:
            print(f"gsc_coverage_error={error}")
        return 1

    print("gsc_coverage_result=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
