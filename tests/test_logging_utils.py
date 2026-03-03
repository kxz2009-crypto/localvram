import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from logging_utils import configure_logging  # noqa: E402


class LoggingUtilsTests(unittest.TestCase):
    def test_configure_logging_respects_level(self):
        logger_name = "unit-test-level"
        with patch.dict("os.environ", {"LV_LOG_LEVEL": "WARNING", "LV_LOG_JSON": "false"}, clear=False):
            logger = configure_logging(logger_name)
        self.assertEqual(logger.level, logging.WARNING)
        self.assertGreaterEqual(len(logger.handlers), 1)

    def test_configure_logging_json_formatter(self):
        logger_name = "unit-test-json"
        with patch.dict("os.environ", {"LV_LOG_LEVEL": "INFO", "LV_LOG_JSON": "true"}, clear=False):
            logger = configure_logging(logger_name)
        self.assertEqual(logger.handlers[0].formatter.__class__.__name__, "JsonFormatter")


if __name__ == "__main__":
    unittest.main()
