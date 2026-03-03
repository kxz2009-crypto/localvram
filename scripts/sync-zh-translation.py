#!/usr/bin/env python3
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
EN_HOME = ROOT / "src" / "pages" / "en" / "index.astro"
ZH_HOME = ROOT / "src" / "pages" / "zh" / "index.astro"
LOGGER = configure_logging("sync-zh-translation")


def main() -> None:
    if not EN_HOME.exists() or not ZH_HOME.exists():
        raise SystemExit("missing source pages")
    LOGGER.info("translation sync placeholder")
    LOGGER.info("en=%s", EN_HOME)
    LOGGER.info("zh=%s", ZH_HOME)


if __name__ == "__main__":
    main()
