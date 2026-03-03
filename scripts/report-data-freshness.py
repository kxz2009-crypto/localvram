#!/usr/bin/env python3
import json
from pathlib import Path

from logging_utils import configure_logging


ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "src" / "data" / "status.json"
LOGGER = configure_logging("report-data-freshness")


def main() -> None:
    status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    LOGGER.info("last_verified=%s", status.get("last_verified"))
    LOGGER.info("last_hardware_sync=%s", status.get("last_hardware_sync"))
    LOGGER.info("freshness_score=%s", status.get("freshness_score"))


if __name__ == "__main__":
    main()
