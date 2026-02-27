#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPPORTUNITIES = ROOT / "src" / "data" / "content-opportunities.json"
DEFAULT_SEARCH_CONSOLE = ROOT / "src" / "data" / "search-console-keywords.json"
DEFAULT_BENCHMARK = ROOT / "src" / "data" / "benchmark-results.json"
DEFAULT_PUBLISH_LOG = ROOT / "src" / "data" / "content-publish-log.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return cleaned or "untitled"


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


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def item_score(item: dict[str, Any]) -> int:
    return (
        int(item.get("search_intent_score", 0))
        * int(item.get("commercial_intent_score", 0))
        * int(item.get("freshness_gap_score", 0))
    )


def topic_key(item: dict[str, Any]) -> str:
    k = slugify(str(item.get("keyword", "")).strip())
    if k and k != "untitled":
        return k
    return slugify(str(item.get("slug", "")).strip())


def dedupe_by_topic(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = topic_key(item)
        if not key or key == "untitled":
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def collect_recent_published_topic_keys(path: Path, cooldown_days: int, now_utc: dt.datetime) -> set[str]:
    payload = load_json(path, {"history": []})
    out: set[str] = set()
    threshold = now_utc - dt.timedelta(days=max(1, int(cooldown_days)))
    for row in payload.get("history", []):
        if not isinstance(row, dict):
            continue
        run_at = parse_iso_utc(str(row.get("run_at", "")))
        if run_at is None or run_at < threshold:
            continue
        for published in row.get("published", []):
            if not isinstance(published, dict):
                continue
            raw_topic_key = slugify(str(published.get("topic_key", "")).strip())
            raw_slug = slugify(str(published.get("slug", "")).strip())
            if raw_topic_key and raw_topic_key != "untitled":
                out.add(raw_topic_key)
            if raw_slug and raw_slug != "untitled":
                out.add(raw_slug)
    return out


def candidate_from_search_console(item: dict[str, Any]) -> dict[str, Any]:
    keyword = str(item.get("keyword", item.get("query", ""))).strip()
    landing = str(item.get("landing", "")).strip()
    clicks = int(item.get("clicks", 0) or 0)
    impressions = int(item.get("impressions", 0) or 0)
    ctr = float(item.get("ctr", 0) or 0)
    position = float(item.get("position", 20) or 20)
    slug_base = landing.strip("/") or keyword
    return {
        "slug": slugify(slug_base),
        "keyword": keyword or slugify(slug_base).replace("-", " "),
        "search_intent_score": clamp(12 - int(position), 3, 10),
        "commercial_intent_score": clamp((clicks // 3) + 3, 3, 10),
        "freshness_gap_score": clamp((impressions // 100) + int(ctr * 100), 3, 10),
    }


def freshness_from_age_days(age_days: int) -> int:
    if age_days <= 1:
        return 10
    if age_days <= 3:
        return 9
    if age_days <= 7:
        return 8
    if age_days <= 14:
        return 7
    if age_days <= 30:
        return 6
    return 5


def candidates_from_benchmark(payload: dict[str, Any], now_utc: dt.datetime, limit: int) -> list[dict[str, Any]]:
    rows = payload.get("models", {})
    if not isinstance(rows, dict):
        return []

    candidates: list[dict[str, Any]] = []
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() != "ok":
            continue

        tps = row.get("tokens_per_second")
        if not isinstance(tps, (int, float)):
            continue

        tested = parse_iso_utc(str(row.get("test_time", "")))
        age_days = 30
        if tested is not None:
            age_days = max(0, int((now_utc - tested).total_seconds() // 86400))

        key = str(tag).strip()
        slug = f"model-{slugify(key.replace(':', '-'))}-benchmark-refresh"
        keyword = f"{key} local inference benchmark update"
        candidates.append(
            {
                "slug": slug,
                "keyword": keyword,
                "search_intent_score": clamp(int(float(tps) // 18) + 4, 4, 10),
                "commercial_intent_score": clamp(int(float(tps) // 24) + 5, 5, 10),
                "freshness_gap_score": freshness_from_age_days(age_days),
            }
        )

    candidates.sort(key=lambda x: (-item_score(x), x.get("slug", "")))
    return candidates[: max(1, int(limit))]


def next_refresh_at(now_utc: dt.datetime, cadence: str) -> str:
    cadence_days = 7 if str(cadence).strip().lower() == "weekly" else 7
    nxt = (now_utc + dt.timedelta(days=cadence_days)).date()
    return f"{nxt.isoformat()}T00:00:00Z"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh content opportunities pool with weekly rotation.")
    parser.add_argument("--opportunities-file", default=str(DEFAULT_OPPORTUNITIES))
    parser.add_argument("--search-console-file", default=str(DEFAULT_SEARCH_CONSOLE))
    parser.add_argument("--benchmark-file", default=str(DEFAULT_BENCHMARK))
    parser.add_argument("--publish-log-file", default=str(DEFAULT_PUBLISH_LOG))
    parser.add_argument("--target-size", type=int, default=0)
    parser.add_argument("--replace-count", type=int, default=0)
    parser.add_argument("--cooldown-days", type=int, default=0)
    parser.add_argument("--benchmark-candidate-limit", type=int, default=160)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now_utc = dt.datetime.now(dt.timezone.utc)
    opportunities_path = Path(args.opportunities_file)
    sc_path = Path(args.search_console_file)
    benchmark_path = Path(args.benchmark_file)
    publish_log_path = Path(args.publish_log_file)

    payload = load_json(opportunities_path, {"updated_at": "", "rotation_policy": {}, "items": []})
    policy = payload.get("rotation_policy", {})
    if not isinstance(policy, dict):
        policy = {}

    target_size = int(args.target_size) if int(args.target_size) > 0 else int(policy.get("target_pool_size", 30) or 30)
    replace_count = int(args.replace_count) if int(args.replace_count) > 0 else int(policy.get("weekly_replace_count", 8) or 8)
    cooldown_days = int(args.cooldown_days) if int(args.cooldown_days) > 0 else int(policy.get("cooldown_days", 30) or 30)
    refresh_cadence = str(policy.get("refresh_cadence", "weekly")).strip() or "weekly"

    current_items = payload.get("items", [])
    if not isinstance(current_items, list):
        current_items = []
    current_items = [row for row in current_items if isinstance(row, dict)]
    current_items = dedupe_by_topic(current_items)

    blocked_topic_keys = collect_recent_published_topic_keys(publish_log_path, cooldown_days, now_utc)

    sc_payload = load_json(sc_path, {"items": []})
    sc_items = sc_payload.get("items", []) if isinstance(sc_payload, dict) else []
    sc_candidates = [candidate_from_search_console(row) for row in sc_items if isinstance(row, dict)]

    benchmark_payload = load_json(benchmark_path, {"models": {}})
    benchmark_candidates = candidates_from_benchmark(benchmark_payload, now_utc, limit=int(args.benchmark_candidate_limit))

    candidate_pool = dedupe_by_topic(sc_candidates + benchmark_candidates)

    existing_topic_keys = {topic_key(item) for item in current_items}
    candidate_pool = [
        item
        for item in candidate_pool
        if topic_key(item) not in existing_topic_keys and topic_key(item) not in blocked_topic_keys
    ]
    candidate_pool.sort(key=lambda x: (-item_score(x), x.get("slug", "")))
    incoming = candidate_pool[: max(1, min(replace_count, target_size))]

    def current_rank(item: dict[str, Any]) -> tuple[int, str]:
        key = topic_key(item)
        base = item_score(item)
        if key in blocked_topic_keys:
            base -= 1000
        return (base, str(item.get("slug", "")))

    current_ranked = sorted(current_items, key=current_rank, reverse=True)
    keep_count = max(0, target_size - len(incoming))
    preserved = current_ranked[:keep_count]

    combined = preserved + incoming
    combined = dedupe_by_topic(combined)

    if len(combined) < target_size:
        fallback = [item for item in current_ranked if topic_key(item) not in {topic_key(x) for x in combined}]
        for item in fallback:
            combined.append(item)
            if len(combined) >= target_size:
                break

    combined = combined[:target_size]
    combined.sort(key=lambda x: (-item_score(x), x.get("slug", "")))

    previous_keys = {topic_key(item) for item in current_items}
    current_keys = {topic_key(item) for item in combined}
    added_keys = sorted(current_keys - previous_keys)
    removed_keys = sorted(previous_keys - current_keys)

    payload["updated_at"] = now_utc.isoformat().replace("+00:00", "Z")
    payload["rotation_policy"] = {
        **policy,
        "target_pool_size": target_size,
        "weekly_replace_count": replace_count,
        "cooldown_days": cooldown_days,
        "refresh_cadence": refresh_cadence,
        "last_refresh_at": now_utc.isoformat().replace("+00:00", "Z"),
        "next_refresh_at": next_refresh_at(now_utc, refresh_cadence),
        "last_refresh_summary": {
            "incoming_count": len(added_keys),
            "removed_count": len(removed_keys),
            "incoming_topic_keys": added_keys[:20],
            "removed_topic_keys": removed_keys[:20],
            "blocked_recent_topic_count": len(blocked_topic_keys),
        },
    }
    payload["items"] = combined

    if not args.dry_run:
        save_json(opportunities_path, payload)

    print(f"opportunities_file={opportunities_path}")
    print(f"target_size={target_size}")
    print(f"replace_count={replace_count}")
    print(f"current_size={len(combined)}")
    print(f"incoming_count={len(added_keys)}")
    print(f"removed_count={len(removed_keys)}")
    if added_keys:
        print("incoming_topic_keys=" + ",".join(added_keys[:12]))
    if removed_keys:
        print("removed_topic_keys=" + ",".join(removed_keys[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
