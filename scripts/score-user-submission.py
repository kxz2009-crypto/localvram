#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "data" / "community-reports.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--score", type=float, default=0.85)
    args = parser.parse_args()

    if OUT.exists():
        payload = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        payload = {"version": "2026.02.22", "reports": []}

    payload["reports"].append(
        {
            "model_id": args.model_id,
            "hardware": args.hardware,
            "precheck_score": args.score,
            "status": "pending_manual_review",
        }
    )
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("submission scored and queued")


if __name__ == "__main__":
    main()
