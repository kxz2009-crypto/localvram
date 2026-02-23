#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EN_HOME = ROOT / "src" / "pages" / "en" / "index.astro"
ZH_HOME = ROOT / "src" / "pages" / "zh" / "index.astro"


def main() -> None:
    if not EN_HOME.exists() or not ZH_HOME.exists():
        raise SystemExit("missing source pages")
    print("translation sync placeholder")
    print(f"en={EN_HOME}")
    print(f"zh={ZH_HOME}")


if __name__ == "__main__":
    main()
