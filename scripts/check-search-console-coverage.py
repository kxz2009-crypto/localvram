#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
LOCALE_RE = re.compile(r"^[a-z]{2}$")
LOGGER = configure_logging("check-search-console-coverage")


def emit(message: str, *, level: str = "info", stderr: bool = False) -> None:
    if level == "error":
        LOGGER.error("%s", message)
    elif level == "warning":
        LOGGER.warning("%s", message)
    else:
        LOGGER.info("%s", message)


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


def parse_expected_sources(raw: str) -> set[str]:
    return {chunk.strip() for chunk in str(raw or "").split(",") if chunk.strip()}


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


def validate_search_console_coverage(
    *,
    file_path: Path,
    required_locales: list[str],
    max_age_hours: int,
    min_items_per_locale: int,
    expected_sources: set[str],
    allow_stub: bool,
) -> dict:
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
        stale = age.total_seconds() > max(0, int(max_age_hours)) * 3600

    missing_locales = sorted(
        [locale for locale, count in counts.items() if count < max(0, int(min_items_per_locale))]
    )
    source_ok = source in expected_sources

    errors: list[str] = []
    if stale:
        errors.append(f"stale_data(max_age_hours={max_age_hours})")
    if not source_ok and not allow_stub:
        expected = ",".join(sorted(expected_sources)) or "unknown"
        errors.append(f"unexpected_source(expected={expected}, got={source or 'unknown'})")
    if missing_locales:
        errors.append("missing_locales=" + ",".join(missing_locales))

    return {
        "errors": errors,
        "counts": counts,
        "source": source,
        "updated_at_raw": updated_at_raw,
        "age_hours": age_hours,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Search Console snapshot coverage for locale KPI refresh.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to search-console-keywords.json")
    parser.add_argument("--locales", default="en", help="Required locales CSV")
    parser.add_argument("--max-age-hours", type=int, default=96, help="Maximum allowed data age")
    parser.add_argument("--min-items-per-locale", type=int, default=1, help="Minimum keyword rows per locale")
    parser.add_argument(
        "--expected-source",
        default="google-search-console-api,google-search-console-ui-export",
        help="Comma-separated expected snapshot sources",
    )
    parser.add_argument("--allow-stub-data", choices=["true", "false"], default="false")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = (ROOT / file_path).resolve()

    required_locales = parse_locales(args.locales)
    if not required_locales:
        emit("gsc_coverage_error=no_valid_locales", level="error")
        return 1

    if not file_path.exists():
        emit(f"gsc_coverage_error=missing_file path={file_path}", level="error")
        return 1

    allow_stub = str(args.allow_stub_data).strip().lower() == "true"
    report = validate_search_console_coverage(
        file_path=file_path,
        required_locales=required_locales,
        max_age_hours=int(args.max_age_hours),
        min_items_per_locale=int(args.min_items_per_locale),
        expected_sources=parse_expected_sources(args.expected_source),
        allow_stub=allow_stub,
    )

    emit(f"gsc_file={file_path}")
    emit(f"gsc_updated_at={report['updated_at_raw'] or 'unknown'}")
    emit(f"gsc_age_hours={report['age_hours']}")
    emit(f"gsc_source={report['source'] or 'unknown'}")
    counts = report["counts"]
    emit("gsc_locale_counts=" + ",".join([f"{locale}:{counts.get(locale, 0)}" for locale in required_locales]))

    if report["errors"]:
        emit("gsc_coverage_result=failed", level="error")
        for error in report["errors"]:
            emit(f"gsc_coverage_error={error}", level="error")
        return 1

    emit("gsc_coverage_result=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
