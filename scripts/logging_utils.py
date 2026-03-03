#!/usr/bin/env python3
"""Shared logging helpers for repository scripts."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


_DEFAULT_LEVEL = "INFO"
_LOG_LEVEL_ENV = "LV_LOG_LEVEL"
_LOG_JSON_ENV = "LV_LOG_JSON"
_SCRIPT_ENV = "LV_SCRIPT_NAME"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _resolve_level(raw: str) -> int:
    level_name = str(raw or _DEFAULT_LEVEL).strip().upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging(script_name: str) -> logging.Logger:
    level = _resolve_level(os.getenv(_LOG_LEVEL_ENV, _DEFAULT_LEVEL))
    use_json = str(os.getenv(_LOG_JSON_ENV, "false")).strip().lower() in {"1", "true", "yes", "on"}
    logger_name = str(script_name or os.getenv(_SCRIPT_ENV, "script")).strip() or "script"

    logger = logging.getLogger(logger_name)
    if logger.handlers:
        logger.setLevel(level)
        return logger

    handler = logging.StreamHandler(stream=sys.stdout)
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
