#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_FILE = ROOT / "src" / "data" / "content-opportunities.json"


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
    print("daily content candidates:")
    for idx, item in enumerate(selected, start=1):
        print(f"{idx}. {item['slug']} ({item['keyword']}) score={score(item)}")


if __name__ == "__main__":
    main()
