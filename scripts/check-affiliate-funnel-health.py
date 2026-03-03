#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FUNNEL_FILE = ROOT / "src" / "data" / "conversion-funnel.json"
LOGGER = configure_logging("check-affiliate-funnel-health")


def parse_iso_utc(value: str) -> dt.datetime | None:
    raw = str(value or "").strip()
    if not raw:
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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"funnel file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid funnel payload: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate affiliate conversion funnel health.")
    parser.add_argument("--funnel-file", default=str(DEFAULT_FUNNEL_FILE))
    parser.add_argument("--min-organic-clicks-for-zero-alert", type=int, default=20)
    parser.add_argument("--max-search-console-age-hours", type=int, default=240)
    parser.add_argument("--allow-zero-affiliate", action="store_true")
    args = parser.parse_args()

    payload = load_json(Path(args.funnel_file))
    funnel = payload.get("funnel", {}) if isinstance(payload.get("funnel"), dict) else {}
    sources = payload.get("sources", {}) if isinstance(payload.get("sources"), dict) else {}
    data_quality = payload.get("data_quality", {}) if isinstance(payload.get("data_quality"), dict) else {}

    organic_clicks = int(funnel.get("organic_search_clicks", 0) or 0)
    affiliate_clicks = int(funnel.get("affiliate_redirect_clicks", 0) or 0)
    cloud_clicks = int(funnel.get("cloud_redirect_clicks", 0) or 0)
    hardware_clicks = int(funnel.get("hardware_redirect_clicks", 0) or 0)
    has_feed = bool(data_quality.get("has_affiliate_event_feed"))

    if not has_feed:
        raise SystemExit("affiliate funnel unhealthy: no affiliate event feed data")

    if (
        not args.allow_zero_affiliate
        and organic_clicks >= max(0, int(args.min_organic_clicks_for_zero_alert))
        and affiliate_clicks <= 0
    ):
        raise SystemExit(
            f"affiliate funnel unhealthy: affiliate clicks are zero while organic clicks are {organic_clicks}"
        )

    updated_raw = str(sources.get("search_console_updated_at", "")).strip()
    updated_at = parse_iso_utc(updated_raw)
    if updated_at is None:
        raise SystemExit("affiliate funnel unhealthy: missing sources.search_console_updated_at")
    age_hours = (dt.datetime.now(dt.timezone.utc) - updated_at).total_seconds() / 3600.0
    if age_hours > max(1, int(args.max_search_console_age_hours)):
        raise SystemExit(
            "affiliate funnel unhealthy: search console snapshot is stale "
            f"({age_hours:.1f}h > {int(args.max_search_console_age_hours)}h)"
        )

    LOGGER.info(
        "affiliate_funnel_ok search=%d affiliate=%d cloud=%d hardware=%d feed=%s sc_age_hours=%.1f",
        organic_clicks,
        affiliate_clicks,
        cloud_clicks,
        hardware_clicks,
        has_feed,
        age_hours,
    )


if __name__ == "__main__":
    main()
