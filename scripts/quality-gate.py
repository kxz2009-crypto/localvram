#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "src" / "data" / "models.json",
    ROOT / "src" / "data" / "status.json",
    ROOT / "src" / "data" / "cta-rules.json",
    ROOT / "src" / "data" / "affiliate-links.json",
]


def main() -> None:
    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print("quality gate failed: missing required files")
        for item in missing:
            print(f"- {item}")
        sys.exit(1)

    links = json.loads((ROOT / "src" / "data" / "affiliate-links.json").read_text(encoding="utf-8"))
    unresolved = [k for k, v in links.items() if "example.com" in v]
    if unresolved:
        print("quality gate warning: unresolved affiliate placeholders")
        for key in unresolved:
            print(f"- {key}")
    else:
        print("affiliate links configured")

    print("quality gate passed")


if __name__ == "__main__":
    main()
