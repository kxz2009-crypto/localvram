#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_FILE = ROOT / "src" / "data" / "affiliate-click-events.json"

KNOWN_PROVIDERS = {"runpod", "vast", "amazon"}


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


def to_iso_utc(parsed: dt.datetime) -> str:
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def extract_event_candidate(obj: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    if "value" in obj:
        value = obj.get("value")
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, dict):
                return decoded
        elif isinstance(value, dict):
            return value
    if "event" in obj and isinstance(obj.get("event"), dict):
        return obj.get("event")
    if any(key in obj for key in ("ts", "timestamp", "provider", "route", "destination", "referer", "referrer")):
        return obj
    return None


def load_source_events(path: Path, source_format: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"source file not found: {path}")

    format_name = source_format
    if format_name == "auto":
        suffix = path.suffix.lower()
        if suffix in {".jsonl", ".ndjson"}:
            format_name = "jsonl"
        else:
            format_name = "json"

    events: list[dict[str, Any]] = []
    if format_name == "jsonl":
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                candidate = extract_event_candidate(parsed)
                if isinstance(candidate, dict):
                    events.append(candidate)
    elif format_name == "json":
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    candidate = extract_event_candidate(item)
                    if isinstance(candidate, dict):
                        events.append(candidate)
        elif isinstance(parsed, dict):
            if isinstance(parsed.get("events"), list):
                for item in parsed.get("events", []):
                    if isinstance(item, dict):
                        candidate = extract_event_candidate(item)
                        if isinstance(candidate, dict):
                            events.append(candidate)
            elif isinstance(parsed.get("items"), list):
                for item in parsed.get("items", []):
                    if isinstance(item, dict):
                        candidate = extract_event_candidate(item)
                        if isinstance(candidate, dict):
                            events.append(candidate)
            elif isinstance(parsed.get("result"), list):
                for item in parsed.get("result", []):
                    if isinstance(item, dict):
                        candidate = extract_event_candidate(item)
                        if isinstance(candidate, dict):
                            events.append(candidate)
            else:
                candidate = extract_event_candidate(parsed)
                if isinstance(candidate, dict):
                    events.append(candidate)
    else:
        raise SystemExit(f"unsupported source format: {source_format}")
    return events


def sanitize_event(raw: dict[str, Any], now: dt.datetime) -> dict[str, Any] | None:
    ts_raw = str(raw.get("ts") or raw.get("timestamp") or raw.get("time") or "").strip()
    parsed = parse_iso_utc(ts_raw)
    if parsed is None:
        parsed = now

    provider = str(raw.get("provider", "")).strip().lower() or "unknown"
    if provider not in KNOWN_PROVIDERS:
        provider = "unknown"

    route = str(raw.get("route") or raw.get("path") or raw.get("request_path") or "").strip()
    destination = str(raw.get("destination") or raw.get("url") or "").strip()
    referer = str(raw.get("referer") or raw.get("referrer") or "").strip()
    campaign = str(raw.get("campaign") or raw.get("utm_campaign") or "").strip()

    if not route and not destination:
        return None

    out = {
        "ts": to_iso_utc(parsed),
        "provider": provider,
        "route": route,
        "destination": destination,
        "referer": referer,
    }
    if campaign:
        out["campaign"] = campaign
    return out


def event_fingerprint(event: dict[str, Any]) -> str:
    payload = "|".join(
        [
            str(event.get("ts", "")).strip(),
            str(event.get("provider", "")).strip(),
            str(event.get("route", "")).strip(),
            str(event.get("destination", "")).strip(),
            str(event.get("referer", "")).strip(),
            str(event.get("campaign", "")).strip(),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import/sanitize affiliate click events into src/data/affiliate-click-events.json")
    parser.add_argument("--source-file", required=True, help="Raw export file path (json/jsonl/ndjson)")
    parser.add_argument("--target-file", default=str(DEFAULT_TARGET_FILE))
    parser.add_argument("--source-format", choices=["auto", "json", "jsonl"], default="auto")
    parser.add_argument("--source-label", default="cloudflare_kv_import")
    parser.add_argument("--max-age-days", type=int, default=45)
    parser.add_argument("--max-events", type=int, default=10000)
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=max(1, int(args.max_age_days)))
    max_events = max(100, int(args.max_events))

    source_path = Path(args.source_file)
    target_path = Path(args.target_file)

    raw_events = load_source_events(source_path, args.source_format)
    existing_payload = load_json(target_path, {"updated_at": "", "source": "", "events": []})
    existing_events = existing_payload.get("events", []) if isinstance(existing_payload, dict) else []
    if not isinstance(existing_events, list):
        existing_events = []

    combined: list[dict[str, Any]] = []
    invalid_count = 0

    for item in existing_events:
        if not isinstance(item, dict):
            continue
        sanitized = sanitize_event(item, now=now)
        if sanitized is None:
            invalid_count += 1
            continue
        parsed = parse_iso_utc(str(sanitized.get("ts", "")))
        if parsed is None or parsed < cutoff:
            continue
        combined.append(sanitized)

    for item in raw_events:
        sanitized = sanitize_event(item, now=now)
        if sanitized is None:
            invalid_count += 1
            continue
        parsed = parse_iso_utc(str(sanitized.get("ts", "")))
        if parsed is None or parsed < cutoff:
            continue
        combined.append(sanitized)

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in combined:
        fp = event_fingerprint(event)
        if fp in seen:
            continue
        seen.add(fp)
        deduped.append(event)

    deduped.sort(key=lambda e: str(e.get("ts", "")), reverse=True)
    deduped = deduped[:max_events]

    out = {
        "updated_at": to_iso_utc(now),
        "source": str(args.source_label).strip() or "cloudflare_kv_import",
        "events": deduped,
    }
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"source_file={source_path}")
    print(f"target_file={target_path}")
    print(f"raw_events={len(raw_events)}")
    print(f"events_after_merge={len(combined)}")
    print(f"events_after_dedupe={len(deduped)}")
    print(f"invalid_or_dropped={invalid_count}")


if __name__ == "__main__":
    main()
