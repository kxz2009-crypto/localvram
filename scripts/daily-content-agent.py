#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_FILE = ROOT / "src" / "data" / "content-opportunities.json"
SC_FILE = ROOT / "src" / "data" / "search-console-keywords.json"
UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"


def score(item: dict) -> int:
    return (
        int(item.get("search_intent_score", 0))
        * int(item.get("commercial_intent_score", 0))
        * int(item.get("freshness_gap_score", 0))
    )


def main() -> None:
    data = json.loads(OPPORTUNITY_FILE.read_text(encoding="utf-8-sig"))
    ranked = sorted(data.get("items", []), key=score, reverse=True)
    selected = ranked[:2]

    if SC_FILE.exists():
        sc_data = json.loads(SC_FILE.read_text(encoding="utf-8-sig"))
        sc_ranked = sorted(sc_data.get("items", []), key=lambda x: x.get("clicks", 0) * x.get("ctr", 0), reverse=True)
        for item in sc_ranked[:2]:
            selected.append(
                {
                    "slug": item.get("landing", "/").strip("/").replace("/", "-"),
                    "keyword": item.get("keyword", item.get("query", "")),
                    "search_intent_score": min(10, max(1, 11 - int(item.get("position", 10)))),
                    "commercial_intent_score": min(10, max(1, int(item.get("clicks", 0) / 3) + 1)),
                    "freshness_gap_score": min(10, max(1, int(item.get("impressions", 0) / 80))),
                }
            )

    today = dt.date.today().isoformat()
    if UPDATES_FILE.exists():
        updates = json.loads(UPDATES_FILE.read_text(encoding="utf-8-sig"))
    else:
        updates = {"items": []}

    updates["items"] = [item for item in updates.get("items", []) if item.get("date") != today]
    updates["items"].insert(
        0,
        {
            "date": today,
            "summary": "Agent-ranked SEO candidates generated from opportunities + Search Console backfeed.",
            "candidates": [
                {"slug": item["slug"], "keyword": item["keyword"], "score": score(item)}
                for item in selected
            ],
        },
    )
    updates["items"] = updates["items"][:30]
    UPDATES_FILE.write_text(json.dumps(updates, ensure_ascii=False, indent=2), encoding="utf-8")

    print("daily content candidates:")
    for idx, item in enumerate(selected, start=1):
        print(f"{idx}. {item['slug']} ({item['keyword']}) score={score(item)}")
    print(f"updated {UPDATES_FILE}")


if __name__ == "__main__":
    main()
