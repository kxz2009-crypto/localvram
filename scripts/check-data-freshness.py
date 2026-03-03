#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_FILE = ROOT / "src" / "data" / "status.json"
DEFAULT_SEARCH_CONSOLE_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
LOGGER = configure_logging("check-data-freshness")


def parse_iso_utc(value: str) -> dt.datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if len(raw) == 10:
        try:
            return dt.datetime.fromisoformat(raw).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def age_hours(now_utc: dt.datetime, parsed: dt.datetime | None) -> float:
    if parsed is None:
        return -1.0
    delta = now_utc - parsed
    return round(delta.total_seconds() / 3600.0, 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check status/search-console freshness and exit non-zero when stale.")
    parser.add_argument("--status-file", default=str(DEFAULT_STATUS_FILE))
    parser.add_argument("--search-console-file", default=str(DEFAULT_SEARCH_CONSOLE_FILE))
    parser.add_argument("--max-status-age-hours", type=int, default=192)
    parser.add_argument("--max-hardware-sync-age-hours", type=int, default=192)
    parser.add_argument("--max-search-console-age-hours", type=int, default=120)
    parser.add_argument("--min-freshness-score", type=int, default=70)
    parser.add_argument("--report-file", default="")
    args = parser.parse_args()

    now_utc = dt.datetime.now(dt.timezone.utc)

    status_path = Path(args.status_file)
    if not status_path.is_absolute():
        status_path = (ROOT / status_path).resolve()
    sc_path = Path(args.search_console_file)
    if not sc_path.is_absolute():
        sc_path = (ROOT / sc_path).resolve()

    errors: list[str] = []

    if not status_path.exists():
        errors.append(f"missing_status_file={status_path}")
        status_payload: dict = {}
    else:
        status_payload = json.loads(status_path.read_text(encoding="utf-8-sig"))

    if not sc_path.exists():
        errors.append(f"missing_search_console_file={sc_path}")
        sc_payload: dict = {}
    else:
        sc_payload = json.loads(sc_path.read_text(encoding="utf-8-sig"))

    last_verified_raw = str(status_payload.get("last_verified", "")).strip()
    last_hardware_sync_raw = str(status_payload.get("last_hardware_sync", "")).strip()
    freshness_score_raw = status_payload.get("freshness_score", 0)
    search_console_updated_raw = str(sc_payload.get("updated_at", "")).strip()

    last_verified_at = parse_iso_utc(last_verified_raw)
    last_hardware_sync_at = parse_iso_utc(last_hardware_sync_raw)
    search_console_updated_at = parse_iso_utc(search_console_updated_raw)

    last_verified_age_h = age_hours(now_utc, last_verified_at)
    last_hardware_sync_age_h = age_hours(now_utc, last_hardware_sync_at)
    search_console_age_h = age_hours(now_utc, search_console_updated_at)

    try:
        freshness_score = int(freshness_score_raw)
    except (TypeError, ValueError):
        freshness_score = -1

    if last_verified_at is None:
        errors.append("invalid_last_verified")
    elif last_verified_age_h > max(0, int(args.max_status_age_hours)):
        errors.append(
            f"status_last_verified_stale(age_hours={last_verified_age_h}, max_hours={int(args.max_status_age_hours)})"
        )

    if last_hardware_sync_at is None:
        errors.append("invalid_last_hardware_sync")
    elif last_hardware_sync_age_h > max(0, int(args.max_hardware_sync_age_hours)):
        errors.append(
            "status_last_hardware_sync_stale("
            f"age_hours={last_hardware_sync_age_h}, max_hours={int(args.max_hardware_sync_age_hours)})"
        )

    if search_console_updated_at is None:
        errors.append("invalid_search_console_updated_at")
    elif search_console_age_h > max(0, int(args.max_search_console_age_hours)):
        errors.append(
            f"search_console_stale(age_hours={search_console_age_h}, max_hours={int(args.max_search_console_age_hours)})"
        )

    if freshness_score < int(args.min_freshness_score):
        errors.append(
            f"freshness_score_too_low(value={freshness_score}, min={int(args.min_freshness_score)})"
        )

    report = {
        "checked_at": now_utc.isoformat().replace("+00:00", "Z"),
        "inputs": {
            "status_file": str(status_path),
            "search_console_file": str(sc_path),
            "max_status_age_hours": int(args.max_status_age_hours),
            "max_hardware_sync_age_hours": int(args.max_hardware_sync_age_hours),
            "max_search_console_age_hours": int(args.max_search_console_age_hours),
            "min_freshness_score": int(args.min_freshness_score),
        },
        "status": {
            "last_verified": last_verified_raw,
            "last_verified_age_hours": last_verified_age_h,
            "last_hardware_sync": last_hardware_sync_raw,
            "last_hardware_sync_age_hours": last_hardware_sync_age_h,
            "freshness_score": freshness_score,
        },
        "search_console": {
            "updated_at": search_console_updated_raw,
            "updated_age_hours": search_console_age_h,
            "items_count": len(sc_payload.get("items", [])) if isinstance(sc_payload.get("items", []), list) else 0,
        },
        "result": "ok" if not errors else "failed",
        "errors": errors,
    }

    LOGGER.info("freshness_checked_at=%s", report["checked_at"])
    LOGGER.info("status_last_verified=%s age_hours=%s", last_verified_raw or "unknown", last_verified_age_h)
    LOGGER.info("status_last_hardware_sync=%s age_hours=%s", last_hardware_sync_raw or "unknown", last_hardware_sync_age_h)
    LOGGER.info("status_freshness_score=%s", freshness_score)
    LOGGER.info("search_console_updated_at=%s age_hours=%s", search_console_updated_raw or "unknown", search_console_age_h)

    if args.report_file:
        report_path = Path(args.report_file)
        if not report_path.is_absolute():
            report_path = (ROOT / report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("report_file=%s", report_path)

    if errors:
        LOGGER.error("freshness_result=failed errors=%s", ",".join(errors))
        return 1

    LOGGER.info("freshness_result=ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
