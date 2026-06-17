#!/usr/bin/env python3
import argparse
import csv
import json
import sys
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
LOGGER = configure_logging("check-status-kpi-data")
DEFAULT_SEARCH_CONSOLE_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
DEFAULT_LOCALE_KPI_FILE = ROOT / "docs" / "seo-ops" / "locale-kpi-tracker.csv"
EXPECTED_LOCALES = {"ar", "de", "es", "fr", "hi", "id", "ja", "ko", "pt", "ru"}
REQUIRED_KPI_COLUMNS = {
    "date",
    "domain",
    "locale",
    "indexed_urls",
    "discovered_urls",
    "index_rate_pct",
    "impressions",
    "clicks",
    "ctr_pct",
    "avg_position",
    "next_action",
}


def _number(value: object, field_name: str, errors: list[str], *, minimum: float = 0) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        errors.append(f"{field_name} must be numeric")
        return 0.0
    if number < minimum:
        errors.append(f"{field_name} must be >= {minimum:g}")
    return number


def validate_status_kpi_data(
    *,
    search_console_file: Path = DEFAULT_SEARCH_CONSOLE_FILE,
    locale_kpi_file: Path = DEFAULT_LOCALE_KPI_FILE,
    expected_locales: set[str] = EXPECTED_LOCALES,
    min_search_rows: int = 1,
) -> dict[str, object]:
    errors: list[str] = []

    if not search_console_file.exists():
        errors.append(f"missing Search Console file: {search_console_file}")
        search_console = {}
    else:
        search_console = json.loads(search_console_file.read_text(encoding="utf-8-sig"))

    search_items = search_console.get("items", []) if isinstance(search_console, dict) else []
    if not isinstance(search_items, list):
        errors.append("Search Console items must be a list")
        search_items = []
    if len(search_items) < min_search_rows:
        errors.append(f"Search Console needs at least {min_search_rows} item(s) for /en/status/")

    search_locales = {str(row.get("locale", "")).strip() for row in search_items if isinstance(row, dict)}
    if not search_locales:
        errors.append("Search Console items must include locale values")
    for index, row in enumerate(search_items[:20], start=1):
        if not isinstance(row, dict):
            errors.append(f"Search Console row {index} must be an object")
            continue
        if not str(row.get("landing", "")).strip():
            errors.append(f"Search Console row {index} missing landing")
        if not (str(row.get("query", "")).strip() or str(row.get("keyword", "")).strip()):
            errors.append(f"Search Console row {index} missing query/keyword")
        _number(row.get("impressions", 0), f"Search Console row {index} impressions", errors)
        _number(row.get("clicks", 0), f"Search Console row {index} clicks", errors)
        _number(row.get("position", 0), f"Search Console row {index} position", errors)

    if not locale_kpi_file.exists():
        errors.append(f"missing locale KPI file: {locale_kpi_file}")
        kpi_rows: list[dict[str, str]] = []
    else:
        with locale_kpi_file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            missing_columns = sorted(REQUIRED_KPI_COLUMNS - fieldnames)
            if missing_columns:
                errors.append(f"locale KPI missing columns: {', '.join(missing_columns)}")
            kpi_rows = list(reader)

    if not kpi_rows:
        errors.append("locale KPI needs at least one row for /en/status/")

    kpi_locales = {str(row.get("locale", "")).strip() for row in kpi_rows}
    missing_locales = sorted(expected_locales - kpi_locales)
    if missing_locales:
        errors.append(f"locale KPI missing expected locales: {', '.join(missing_locales)}")

    for index, row in enumerate(kpi_rows, start=1):
        locale = str(row.get("locale", "")).strip() or f"row {index}"
        if not str(row.get("date", "")).strip():
            errors.append(f"locale KPI {locale} missing date")
        if not str(row.get("next_action", "")).strip():
            errors.append(f"locale KPI {locale} missing next_action")
        indexed = _number(row.get("indexed_urls", 0), f"locale KPI {locale} indexed_urls", errors)
        discovered = _number(row.get("discovered_urls", 0), f"locale KPI {locale} discovered_urls", errors)
        _number(row.get("index_rate_pct", 0), f"locale KPI {locale} index_rate_pct", errors)
        _number(row.get("impressions", 0), f"locale KPI {locale} impressions", errors)
        _number(row.get("clicks", 0), f"locale KPI {locale} clicks", errors)
        _number(row.get("ctr_pct", 0), f"locale KPI {locale} ctr_pct", errors)
        _number(row.get("avg_position", 0), f"locale KPI {locale} avg_position", errors)
        if discovered and indexed > discovered:
            errors.append(f"locale KPI {locale} indexed_urls cannot exceed discovered_urls")

    return {
        "errors": errors,
        "search_rows": len(search_items),
        "search_locales": sorted(x for x in search_locales if x),
        "kpi_rows": len(kpi_rows),
        "kpi_locales": sorted(x for x in kpi_locales if x),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate status page Search Console and locale KPI data.")
    parser.add_argument("--search-console-file", type=Path, default=DEFAULT_SEARCH_CONSOLE_FILE)
    parser.add_argument("--locale-kpi-file", type=Path, default=DEFAULT_LOCALE_KPI_FILE)
    parser.add_argument("--min-search-rows", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = validate_status_kpi_data(
        search_console_file=args.search_console_file,
        locale_kpi_file=args.locale_kpi_file,
        min_search_rows=args.min_search_rows,
    )
    if result["errors"]:
        LOGGER.error("status KPI data check failed")
        for error in result["errors"]:
            LOGGER.error("%s", error)
        sys.exit(1)
    LOGGER.info(
        "status KPI data ok: search_rows=%s search_locales=%s kpi_rows=%s kpi_locales=%s",
        result["search_rows"],
        ",".join(result["search_locales"]),
        result["kpi_rows"],
        ",".join(result["kpi_locales"]),
    )


if __name__ == "__main__":
    main()
