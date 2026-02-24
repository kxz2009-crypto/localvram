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

- Keep disclosure line near CTA modules.
- Use one local recommendation CTA and one cloud fallback CTA.
- Keep wording factual: measured vs estimated must stay explicit.
"""


def main() -> None:
    max_drafts = max(1, int(os.getenv("LV_CONTENT_DRAFT_COUNT", "3")))
    opportunities = load_json(OPPORTUNITY_FILE, {"items": []})
    ranked = sorted(opportunities.get("items", []), key=score, reverse=True)
    seeded = [{**row, "source": "opportunity"} for row in ranked]

    sc_payload = load_json(SC_FILE, {"items": []})
    sc_rows = [candidate_from_sc(item) for item in sc_payload.get("items", [])]
    sc_ranked = sorted(sc_rows, key=score_with_boost, reverse=True)

    combined = dedupe_candidates(seeded + sc_ranked)
    selected = sorted(combined, key=score_with_boost, reverse=True)[:max_drafts]

    links = load_json(AFFILIATE_LINKS_FILE, {"runpod": "/go/runpod", "vast": "/go/vast"})
    measured = pick_measured_highlights(max_count=3)

    today = dt.date.today().isoformat()
    queue_day_dir = QUEUE_DIR / today
    queue_day_dir.mkdir(parents=True, exist_ok=True)

    draft_records = []
    for idx, item in enumerate(selected, start=1):
        slug = slugify(item.get("slug") or item.get("keyword") or f"draft-{idx}")[:80]
        title = build_title(str(item.get("keyword", "")).strip(), today)
        draft_text = draft_markdown(
            title=title,
            keyword=str(item.get("keyword", "")).strip(),
            score_value=score_with_boost(item),
            source=str(item.get("source", "unknown")),
            measured=measured,
            links=links,
            landing=str(item.get("landing", "")).strip(),
            date_iso=today,
        )
        draft_path = queue_day_dir / f"{idx:02d}-{slug}.md"
        draft_path.write_text(draft_text, encoding="utf-8")
        draft_records.append(
            {
                "date": today,
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
    updates["items"] = [row for row in updates.get("items", []) if row.get("date") != today]
    updates["items"].insert(
        0,
        {
            "date": today,
            "summary": "Agent ranked SEO opportunities and generated review-ready content drafts.",
            "candidates": draft_records,
        },
    )
    updates["items"] = updates["items"][:30]
    save_json(UPDATES_FILE, updates)

    draft_index = load_json(DRAFT_INDEX_FILE, {"updated_at": "", "items": []})
    existing = [row for row in draft_index.get("items", []) if row.get("date") != today]
    draft_index["updated_at"] = f"{today}T00:00:00Z"
    draft_index["items"] = (draft_records + existing)[:120]
    save_json(DRAFT_INDEX_FILE, draft_index)

    print("daily content drafts generated:")
    for idx, row in enumerate(draft_records, start=1):
        print(f"{idx}. {row['slug']} | score={row['score']} | {row['draft_path']}")
    print(f"updated {UPDATES_FILE}")
    print(f"updated {DRAFT_INDEX_FILE}")


if __name__ == "__main__":
    main()
