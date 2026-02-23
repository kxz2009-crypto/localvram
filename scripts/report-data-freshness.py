#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "src" / "data" / "status.json"


def main() -> None:
    status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    print(f"last_verified={status.get('last_verified')}")
    print(f"last_hardware_sync={status.get('last_hardware_sync')}")
    print(f"freshness_score={status.get('freshness_score')}")


if __name__ == "__main__":
    main()
