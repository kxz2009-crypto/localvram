#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_CONSOLE_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
DEFAULT_AFFILIATE_EVENTS_FILE = ROOT / "src" / "data" / "affiliate-click-events.json"
DEFAULT_OUT_FILE = ROOT / "src" / "data" / "conversion-funnel.json"

LOCAL_HOSTS = {"localvram.com", "www.localvram.com", "localvram.cn", "www.localvram.cn"}
DECISION_PATH = re.compile(r"^/(?:[a-z]{2}/)?(?:models|tools|errors|hardware|guides|affiliate)/")
LOGGER = configure_logging("build-conversion-funnel")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def parse_click_events(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("events", "items", "clicks"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def safe_path_from_url(raw_url: str) -> str:
    value = str(raw_url or "").strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except ValueError:
        return ""
    return (parsed.path or "") if not parsed.netloc or parsed.hostname in LOCAL_HOSTS else ""


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build conversion funnel snapshot from Search Console and affiliate click exports.")
    parser.add_argument("--search-console-file", default=str(DEFAULT_SEARCH_CONSOLE_FILE))
    parser.add_argument("--affiliate-events-file", default=str(DEFAULT_AFFILIATE_EVENTS_FILE))
    parser.add_argument("--output-file", default=str(DEFAULT_OUT_FILE))
    parser.add_argument("--window-days", type=int, default=30)
    args = parser.parse_args()

    now_utc = dt.datetime.now(dt.timezone.utc)
    window_days = max(1, int(args.window_days))
    window_start = now_utc - dt.timedelta(days=window_days)

    sc_path = Path(args.search_console_file)
    events_path = Path(args.affiliate_events_file)
    out_path = Path(args.output_file)

    sc_payload = load_json(sc_path, {"updated_at": "", "items": []})
    sc_items = sc_payload.get("items", []) if isinstance(sc_payload, dict) else []
    sc_items = [item for item in sc_items if isinstance(item, dict)]

    organic_clicks = 0
    decision_clicks = 0
    landing_counter: Counter[str] = Counter()
    for item in sc_items:
        clicks = int(item.get("clicks", 0) or 0)
        organic_clicks += clicks
        landing = str(item.get("landing", "")).strip() or "/unknown"
        landing_counter[landing] += clicks
        if DECISION_PATH.match(safe_path_from_url(landing)):
            decision_clicks += clicks

    raw_event_payload = load_json(events_path, {"events": []})
    all_events = parse_click_events(raw_event_payload)
    in_window_events: list[dict[str, Any]] = []
    for event in all_events:
        event_time = parse_iso_utc(str(event.get("ts", "")))
        if event_time is None or not window_start <= event_time <= now_utc:
            continue
        in_window_events.append(event)

    provider_counter: Counter[str] = Counter()
    route_counter: Counter[str] = Counter()
    source_page_counter: Counter[str] = Counter()

    for event in in_window_events:
        provider = str(event.get("provider", "")).strip().lower() or "unknown"
        route = str(event.get("route", "")).strip() or "/unknown"
        referer_path = safe_path_from_url(str(event.get("referer", "")))
        if referer_path:
            source_key = referer_path
        else:
            source_key = "unknown"
        provider_counter[provider] += 1
        route_counter[route] += 1
        source_page_counter[source_key] += 1

    affiliate_clicks = len(in_window_events)
    cloud_clicks = int(provider_counter.get("runpod", 0) + provider_counter.get("vast", 0))
    hardware_clicks = int(provider_counter.get("amazon", 0))

    by_provider = []
    for provider, clicks in provider_counter.most_common():
        by_provider.append(
            {
                "provider": provider,
                "clicks": int(clicks),
                "share_pct": percent(int(clicks), affiliate_clicks),
            }
        )

    by_route = []
    for route, clicks in route_counter.most_common(20):
        by_route.append(
            {
                "route": route,
                "clicks": int(clicks),
                "share_pct": percent(int(clicks), affiliate_clicks),
            }
        )

    top_source_pages = []
    for page, clicks in source_page_counter.most_common(20):
        top_source_pages.append(
            {
                "page": page,
                "clicks": int(clicks),
            }
        )

    top_search_landings = []
    for landing, clicks in landing_counter.most_common(20):
        top_search_landings.append(
            {
                "landing": landing,
                "clicks": int(clicks),
                "share_pct": percent(int(clicks), organic_clicks),
            }
        )

    payload = {
        "generated_at": now_utc.isoformat().replace("+00:00", "Z"),
        "window_days": window_days,
        "window_start": window_start.isoformat().replace("+00:00", "Z"),
        "window_end": now_utc.isoformat().replace("+00:00", "Z"),
        "sources": {
            "search_console_file": str(sc_path.relative_to(ROOT)) if sc_path.is_relative_to(ROOT) else str(sc_path),
            "affiliate_events_file": str(events_path.relative_to(ROOT)) if events_path.is_relative_to(ROOT) else str(events_path),
            "search_console_window": sc_payload.get("window", {}) if isinstance(sc_payload, dict) else {},
            "search_console_updated_at": str(sc_payload.get("updated_at", "")) if isinstance(sc_payload, dict) else "",
        },
        "funnel": {
            "organic_search_clicks": int(organic_clicks),
            "decision_page_clicks": int(decision_clicks),
            "affiliate_redirect_clicks": int(affiliate_clicks),
            "cloud_redirect_clicks": int(cloud_clicks),
            "hardware_redirect_clicks": int(hardware_clicks),
            "search_to_affiliate_pct": None,
            "search_to_cloud_pct": None,
            "affiliate_to_cloud_pct": None,
            "cloud_share_of_redirects_pct": percent(cloud_clicks, affiliate_clicks) if affiliate_clicks else None,
        },
        "breakdown": {
            "providers": by_provider,
            "routes": by_route,
            "source_pages": top_source_pages,
            "search_landings": top_search_landings,
        },
        "data_quality": {
            "search_console_items": len(sc_items),
            "affiliate_event_items_total": len(all_events),
            "affiliate_event_items_in_window": len(in_window_events),
            "has_affiliate_event_feed": bool(events_path.exists() and len(all_events) > 0),
            "unattributed_redirects": int(source_page_counter.get("unknown", 0)),
            "excluded_invalid_or_out_of_window_events": len(all_events) - len(in_window_events),
            "conversion_rate_status": "unavailable_no_session_attribution",
            "note": "Search Console query/page totals and redirect request counts are separate datasets with different windows. Requests are not unique people or orders; legacy events may include bots and checks. Conversion rates are unavailable without session attribution and provider order reconciliation.",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("conversion_funnel_out=%s", out_path)
    LOGGER.info(
        "funnel_summary="
        f"search={organic_clicks},decision={decision_clicks},affiliate={affiliate_clicks},cloud={cloud_clicks},hardware={hardware_clicks}"
    )


if __name__ == "__main__":
    main()
