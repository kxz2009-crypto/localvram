#!/usr/bin/env python3
import datetime as dt
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_FILE = ROOT / "src" / "data" / "content-opportunities.json"
UPDATES_FILE = ROOT / "src" / "data" / "daily-updates.json"


def score(item: dict) -> int:
    return (
        int(item.get("search_intent_score", 0))
        * int(item.get("commercial_intent_score", 0))
        * int(item.get("freshness_gap_score", 0))
    )


def main() -> None:
    data = json.loads(OPPORTUNITY_FILE.read_text(encoding="utf-8"))
    ranked = sorted(data.get("items", []), key=score, reverse=True)
    selected = ranked[:3]

    today = dt.date.today().isoformat()
    if UPDATES_FILE.exists():
        updates = json.loads(UPDATES_FILE.read_text(encoding="utf-8"))
    else:
        updates = {"items": []}

    updates["items"] = [item for item in updates.get("items", []) if item.get("date") != today]
    updates["items"].insert(
        0,
        {
            "date": today,
            "summary": "Agent-ranked SEO and content candidates generated.",
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
