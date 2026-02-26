#!/usr/bin/env python3
import argparse
import datetime as dt
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEARCH_CONSOLE_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
DEFAULT_AFFILIATE_EVENTS_FILE = ROOT / "src" / "data" / "affiliate-click-events.json"
DEFAULT_OUT_FILE = ROOT / "src" / "data" / "conversion-funnel.json"

LOCAL_HOSTS = {"localvram.com", "www.localvram.com"}
DECISION_PREFIXES = (
    "/en/models/",
    "/en/tools/",
    "/en/errors/",
    "/en/hardware/",
    "/en/guides/",
    "/en/affiliate/",
)


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
    return parsed.path or ""


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
        if any(landing.startswith(prefix) for prefix in DECISION_PREFIXES):
            decision_clicks += clicks

    raw_event_payload = load_json(events_path, {"events": []})
    all_events = parse_click_events(raw_event_payload)
    in_window_events: list[dict[str, Any]] = []
    for event in all_events:
        event_time = parse_iso_utc(str(event.get("ts", "")))
        if event_time is not None and event_time < window_start:
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
            "search_console_file": str(sc_path.relative_to(ROOT)).replace("\\", "/") if sc_path.exists() else str(sc_path),
            "affiliate_events_file": str(events_path.relative_to(ROOT)).replace("\\", "/") if events_path.exists() else str(events_path),
            "search_console_updated_at": str(sc_payload.get("updated_at", "")) if isinstance(sc_payload, dict) else "",
        },
        "funnel": {
            "organic_search_clicks": int(organic_clicks),
            "decision_page_clicks": int(decision_clicks),
            "affiliate_redirect_clicks": int(affiliate_clicks),
            "cloud_redirect_clicks": int(cloud_clicks),
            "hardware_redirect_clicks": int(hardware_clicks),
            "search_to_affiliate_pct": percent(affiliate_clicks, organic_clicks),
            "search_to_cloud_pct": percent(cloud_clicks, organic_clicks),
            "affiliate_to_cloud_pct": percent(cloud_clicks, affiliate_clicks),
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
            "note": "Affiliate orders/conversions from third-party networks are not included. This report tracks search intent and outbound redirect clicks.",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"conversion_funnel_out={out_path}")
    print(
        "funnel_summary="
        f"search={organic_clicks},decision={decision_clicks},affiliate={affiliate_clicks},cloud={cloud_clicks},hardware={hardware_clicks}"
    )


if __name__ == "__main__":
    main()
