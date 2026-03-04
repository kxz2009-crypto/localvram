#!/usr/bin/env python3
"""Validate recency of manual RTL visual signoff records."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIGNOFF_FILE = ROOT / "docs" / "i18n" / "rtl-visual-signoff.json"
LOGGER = configure_logging("check-rtl-visual-signoff")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate RTL visual signoff recency.")
    parser.add_argument(
        "--signoff-file",
        default=str(DEFAULT_SIGNOFF_FILE),
        help="Path to rtl signoff JSON file.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=8,
        help="Maximum allowed age in days for latest signoff entry.",
    )
    return parser.parse_args()


def parse_entry_date(raw: str) -> date:
    return datetime.strptime(raw, "%Y-%m-%d").date()


def main() -> int:
    args = parse_args()
    signoff_path = Path(args.signoff_file).resolve()
    if not signoff_path.exists():
        LOGGER.error("rtl signoff check failed: missing file: %s", signoff_path)
        return 1

    try:
        payload = json.loads(signoff_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        LOGGER.error("rtl signoff check failed: invalid json: %s", exc)
        return 1

    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        LOGGER.error("rtl signoff check failed: entries must be a non-empty array")
        return 1

    valid_entries: list[tuple[date, dict[str, object]]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_date = entry.get("date")
        if not isinstance(raw_date, str):
            continue
        try:
            entry_date = parse_entry_date(raw_date)
        except ValueError:
            continue
        valid_entries.append((entry_date, entry))

    if not valid_entries:
        LOGGER.error("rtl signoff check failed: no valid dated entries found")
        return 1

    latest_date, latest = max(valid_entries, key=lambda item: item[0])
    latest_status = str(latest.get("status", "")).strip().lower()
    if latest_status != "pass":
        LOGGER.error("rtl signoff check failed: latest status is not pass (status=%s)", latest_status or "missing")
        return 1

    today_utc = datetime.now(timezone.utc).date()
    age_days = (today_utc - latest_date).days
    if age_days < 0:
        LOGGER.error("rtl signoff check failed: latest signoff date is in the future (%s)", latest_date.isoformat())
        return 1
    if age_days > args.max_age_days:
        LOGGER.error(
            "rtl signoff check failed: latest pass is stale (age_days=%s max_age_days=%s date=%s)",
            age_days,
            args.max_age_days,
            latest_date.isoformat(),
        )
        return 1

    reviewer = str(latest.get("reviewer", "")).strip() or "unknown"
    run_id = str(latest.get("run_id", "")).strip() or "n/a"
    LOGGER.info(
        "rtl signoff check passed: date=%s age_days=%s reviewer=%s run_id=%s file=%s",
        latest_date.isoformat(),
        age_days,
        reviewer,
        run_id,
        signoff_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

