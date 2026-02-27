#!/usr/bin/env python3
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_FILE = ROOT / "src" / "data" / "content-opportunities.json"
SC_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"
DRAFT_INDEX_FILE = ROOT / "src" / "data" / "daily-content-drafts.json"
BENCHMARK_FILE = ROOT / "src" / "data" / "benchmark-results.json"
AFFILIATE_LINKS_FILE = ROOT / "src" / "data" / "affiliate-links.json"
PUBLISH_LOG_FILE = ROOT / "src" / "data" / "content-publish-log.json"
BLOG_DIR = ROOT / "src" / "content" / "blog"
QUEUE_DIR = ROOT / "content-queue"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return cleaned or "untitled"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text.strip()
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()
    header = parts[0][4:]
    body = parts[1].strip()
    out: dict[str, str] = {}
    for raw in header.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        k = key.strip()
        v = value.strip()
        if v.startswith('"') and v.endswith('"') and len(v) >= 2:
            v = v[1:-1]
        out[k] = v
    return out, body


def dump_frontmatter(frontmatter: dict[str, str]) -> str:
    lines: list[str] = []
    for key, value in frontmatter.items():
        raw = str(value)
        if re.search(r"[\s:#]", raw) or raw == "":
            escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
            raw = f'"{escaped}"'
        lines.append(f"{key}: {raw}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def archive_stale_queue_drafts(queue_day_dir: Path, marker: str) -> None:
    for stale_file in queue_day_dir.glob("*.md"):
        try:
            raw = stale_file.read_text(encoding="utf-8-sig")
            frontmatter, body = parse_frontmatter(raw)
            if not frontmatter:
                frontmatter = {"title": stale_file.stem}
            frontmatter["status"] = "rejected_manual"
            frontmatter["reviewed_at"] = marker
            content = f"{dump_frontmatter(frontmatter)}\n{body.strip()}\n"
            stale_file.write_text(content, encoding="utf-8")
        except OSError:
            # Stale queue files should not break generation.
            continue


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


def topic_key(item: dict[str, Any]) -> str:
    keyword = slugify(str(item.get("keyword", "")).strip())
    if keyword and keyword != "untitled":
        return keyword
    slug = slugify(str(item.get("slug", "")).strip())
    if slug and slug != "untitled":
        return slug
    return ""


def collect_blocked_topics(today: dt.date, lookback_days: int = 30) -> tuple[set[str], set[str]]:
    blocked_slugs: set[str] = set()
    blocked_topics: set[str] = set()

    if BLOG_DIR.exists():
        for post in BLOG_DIR.glob("*.md"):
            blocked_slugs.add(post.stem.strip().lower())
            raw = post.read_text(encoding="utf-8-sig")
            frontmatter, _ = parse_frontmatter(raw)
            k = slugify(str(frontmatter.get("keyword", "")).strip())
            if k and k != "untitled":
                blocked_topics.add(k)

    publish_log = load_json(PUBLISH_LOG_FILE, {"history": []})
    for run in publish_log.get("history", []):
        if not isinstance(run, dict):
            continue
        for item in run.get("published", []):
            if not isinstance(item, dict):
                continue
            s = slugify(str(item.get("slug", "")).strip())
            if s and s != "untitled":
                blocked_slugs.add(s)
            t = slugify(str(item.get("topic_key", "")).strip())
            if t and t != "untitled":
                blocked_topics.add(t)

    threshold = today - dt.timedelta(days=max(1, int(lookback_days)))
    draft_index = load_json(DRAFT_INDEX_FILE, {"items": []})
    for item in draft_index.get("items", []):
        if not isinstance(item, dict):
            continue
        row_date = str(item.get("date", "")).strip()
        try:
            parsed_date = dt.date.fromisoformat(row_date)
        except ValueError:
            continue
        if parsed_date < threshold:
            continue
        s = slugify(str(item.get("slug", "")).strip())
        if s and s != "untitled":
            blocked_slugs.add(s)
        t = topic_key(item)
        if t:
            blocked_topics.add(t)

    return blocked_slugs, blocked_topics


def score(item: dict[str, Any]) -> int:
    return (
        int(item.get("search_intent_score", 0))
        * int(item.get("commercial_intent_score", 0))
        * int(item.get("freshness_gap_score", 0))
    )


def score_with_boost(item: dict[str, Any]) -> int:
    base = score(item)
    click_boost = int(item.get("clicks", 0))
    ctr_boost = int(float(item.get("ctr", 0)) * 100)
    return base + click_boost + ctr_boost


def candidate_from_sc(item: dict[str, Any]) -> dict[str, Any]:
    landing = str(item.get("landing", "/")).strip()
    keyword = str(item.get("keyword", item.get("query", ""))).strip()
    derived_slug = slugify(landing.strip("/") or keyword)
    return {
        "slug": derived_slug,
        "keyword": keyword,
        "landing": landing,
        "search_intent_score": min(10, max(1, 11 - int(float(item.get("position", 10))))),
        "commercial_intent_score": min(10, max(1, int(item.get("clicks", 0) / 3) + 1)),
        "freshness_gap_score": min(10, max(1, int(item.get("impressions", 0) / 80))),
        "clicks": int(item.get("clicks", 0)),
        "ctr": float(item.get("ctr", 0)),
        "source": "search_console",
    }


def dedupe_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = slugify(item.get("slug") or item.get("keyword") or "")
        if key in seen:
            continue
        seen.add(key)
        item["slug"] = key
        out.append(item)
    return out


def filter_fresh_candidates(
    items: list[dict[str, Any]],
    *,
    blocked_slugs: set[str],
    blocked_topics: set[str],
    min_score: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in sorted(dedupe_candidates(items), key=score_with_boost, reverse=True):
        current_score = score_with_boost(item)
        if current_score < min_score:
            continue
        s = slugify(item.get("slug") or item.get("keyword") or "")
        t = topic_key(item)
        if s in blocked_slugs:
            continue
        if t and t in blocked_topics:
            continue
        blocked_slugs.add(s)
        if t:
            blocked_topics.add(t)
        selected.append(item)
    return selected


def pick_measured_highlights(max_count: int = 3) -> list[dict[str, Any]]:
    payload = load_json(BENCHMARK_FILE, {"models": {}})
    rows = payload.get("models", {})
    if not isinstance(rows, dict):
        return []
    measured = []
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if row.get("status") != "ok":
            continue
        tps = row.get("tokens_per_second")
        if not isinstance(tps, (int, float)):
            continue
        measured.append(
            {
                "tag": str(tag),
                "tokens_per_second": float(tps),
                "latency_ms": float(row.get("latency_ms", 0)),
                "test_time": str(row.get("test_time", "")),
            }
        )
    measured.sort(key=lambda x: x["tokens_per_second"], reverse=True)
    return measured[:max_count]


def build_benchmark_fallback_candidates(max_count: int = 120) -> list[dict[str, Any]]:
    payload = load_json(BENCHMARK_FILE, {"models": {}})
    rows = payload.get("models", {})
    if not isinstance(rows, dict):
        return []

    now_utc = dt.datetime.now(dt.timezone.utc)
    candidates: list[dict[str, Any]] = []
    for tag, row in rows.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() != "ok":
            continue
        tps = row.get("tokens_per_second")
        if not isinstance(tps, (int, float)):
            continue

        tested_at = parse_iso_utc(str(row.get("test_time", "")))
        age_days = 14
        if tested_at is not None:
            age_days = max(0, int((now_utc - tested_at).total_seconds() // 86400))
        freshness_gap = max(3, 10 - min(age_days, 7))
        search_intent = min(10, max(4, int(float(tps) // 15) + 3))
        commercial_intent = min(10, max(4, int(float(tps) // 20) + 4))

        tag_text = str(tag).strip()
        slug = f"model-{slugify(tag_text.replace(':', '-'))}-local-benchmark"
        keyword = f"{tag_text} local inference benchmark"
        candidates.append(
            {
                "slug": slug,
                "keyword": keyword,
                "landing": "/en/models/",
                "search_intent_score": search_intent,
                "commercial_intent_score": commercial_intent,
                "freshness_gap_score": freshness_gap,
                "clicks": 0,
                "ctr": 0.0,
                "source": "benchmark_fallback",
            }
        )

    candidates.sort(key=score_with_boost, reverse=True)
    return candidates[:max_count]


def build_title(keyword: str, date_iso: str) -> str:
    if keyword:
        base = keyword.strip().rstrip("?")
    else:
        base = "local llm deployment"
    year = date_iso.split("-")[0]
    return f"{base.title()}: Practical Guide ({year})"


def draft_markdown(
    *,
    title: str,
    keyword: str,
    score_value: int,
    source: str,
    measured: list[dict[str, Any]],
    links: dict[str, str],
    landing: str,
    date_iso: str,
) -> str:
    measured_lines = []
    for row in measured:
        measured_lines.append(
            f"- `{row['tag']}`: {row['tokens_per_second']:.1f} tok/s (latency {row['latency_ms']:.0f} ms, test {row['test_time']})"
        )
    measured_block = "\n".join(measured_lines) if measured_lines else "- No verified measurements available yet."

    runpod = links.get("runpod", "/go/runpod")
    vast = links.get("vast", "/go/vast")
    hardware = "/en/affiliate/hardware-upgrade/"
    tool = "/en/tools/vram-calculator/"
    landing_ref = landing if landing else "/en/models/"

    return f"""---
title: "{title}"
date: {date_iso}
keyword: "{keyword}"
score: {score_value}
source: {source}
status: draft
---

## Why this topic now

Users searching for "{keyword}" are usually deciding whether to run locally or move to cloud. This draft is generated for editor review and factual expansion.

## Verified benchmark anchor

{measured_block}

## Suggested article structure

1. Define the hardware requirement and failure boundary.
2. Show measured local performance and explain bottlenecks.
3. Compare local cost vs cloud fallback.
4. Give a clear action path based on VRAM and model size.

## Internal links to include

- VRAM calculator: {tool}
- Related landing: {landing_ref}
- Local hardware path: {hardware}
- Cloud fallback: {runpod} and {vast}

## Monetization placement (compliant)

- Affiliate Disclosure: This draft may include affiliate links. LocalVRAM may earn a commission at no extra cost.
- Keep disclosure line near CTA modules.
- Use one local recommendation CTA and one cloud fallback CTA.
- Keep wording factual: measured vs estimated must stay explicit.
"""


def main() -> None:
    max_drafts = max(1, int(os.getenv("LV_CONTENT_DRAFT_COUNT", "3")))
    min_candidate_score = max(0, int(os.getenv("LV_CONTENT_AUTO_PUBLISH_MIN_SCORE", "120")))
    today = dt.date.today()
    today_iso = today.isoformat()
    blocked_slugs, blocked_topics = collect_blocked_topics(today, lookback_days=30)

    opportunities = load_json(OPPORTUNITY_FILE, {"items": []})
    ranked = sorted(opportunities.get("items", []), key=score, reverse=True)
    seeded = [{**row, "source": "opportunity"} for row in ranked]

    sc_payload = load_json(SC_FILE, {"items": []})
    sc_rows = [candidate_from_sc(item) for item in sc_payload.get("items", [])]
    sc_ranked = sorted(sc_rows, key=score_with_boost, reverse=True)

    primary = filter_fresh_candidates(
        seeded + sc_ranked,
        blocked_slugs=blocked_slugs,
        blocked_topics=blocked_topics,
        min_score=min_candidate_score,
    )
    selected = primary[:max_drafts]
    if len(selected) < max_drafts:
        fallback = filter_fresh_candidates(
            build_benchmark_fallback_candidates(max_count=200),
            blocked_slugs=blocked_slugs,
            blocked_topics=blocked_topics,
            min_score=min_candidate_score,
        )
        selected.extend(fallback[: max_drafts - len(selected)])

    links = load_json(AFFILIATE_LINKS_FILE, {"runpod": "/go/runpod", "vast": "/go/vast"})
    measured = pick_measured_highlights(max_count=3)

    queue_day_dir = QUEUE_DIR / today_iso
    queue_day_dir.mkdir(parents=True, exist_ok=True)
    archive_stale_queue_drafts(queue_day_dir, marker=f"{today_iso}T00:00:00Z")

    draft_records = []
    for idx, item in enumerate(selected, start=1):
        slug = slugify(item.get("slug") or item.get("keyword") or f"draft-{idx}")[:80]
        title = build_title(str(item.get("keyword", "")).strip(), today_iso)
        draft_text = draft_markdown(
            title=title,
            keyword=str(item.get("keyword", "")).strip(),
            score_value=score_with_boost(item),
            source=str(item.get("source", "unknown")),
            measured=measured,
            links=links,
            landing=str(item.get("landing", "")).strip(),
            date_iso=today_iso,
        )
        draft_path = queue_day_dir / f"{idx:02d}-{slug}.md"
        draft_path.write_text(draft_text, encoding="utf-8")
        draft_records.append(
            {
                "date": today_iso,
                "slug": slug,
                "title": title,
                "keyword": str(item.get("keyword", "")),
                "score": score_with_boost(item),
                "source": str(item.get("source", "unknown")),
                "landing": str(item.get("landing", "")),
                "draft_path": str(draft_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    updates = load_json(UPDATES_FILE, {"items": []})
    updates["items"] = [row for row in updates.get("items", []) if row.get("date") != today_iso]
    updates["items"].insert(
        0,
        {
            "date": today_iso,
            "summary": "Agent ranked SEO opportunities, filtered repeated topics, and generated review-ready content drafts.",
            "candidates": draft_records,
        },
    )
    updates["items"] = updates["items"][:30]
    save_json(UPDATES_FILE, updates)

    draft_index = load_json(DRAFT_INDEX_FILE, {"updated_at": "", "items": []})
    existing = [row for row in draft_index.get("items", []) if row.get("date") != today_iso]
    draft_index["updated_at"] = f"{today_iso}T00:00:00Z"
    draft_index["items"] = (draft_records + existing)[:120]
    save_json(DRAFT_INDEX_FILE, draft_index)

    print("daily content drafts generated:")
    for idx, row in enumerate(draft_records, start=1):
        print(f"{idx}. {row['slug']} | score={row['score']} | {row['draft_path']}")
    print(f"updated {UPDATES_FILE}")
    print(f"updated {DRAFT_INDEX_FILE}")


if __name__ == "__main__":
    main()
