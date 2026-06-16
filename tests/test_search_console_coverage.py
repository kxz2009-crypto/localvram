import importlib.util
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check-search-console-coverage.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("check_search_console_coverage", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SearchConsoleCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        base_tmp = ROOT / ".tmp" / "unit-tests"
        base_tmp.mkdir(parents=True, exist_ok=True)
        self.tmp_dir = base_tmp / f"gsc-coverage-{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ui_export_source_is_trusted_by_default(self):
        path = self.tmp_dir / "search-console-keywords.json"
        path.write_text(
            json.dumps(
                {
                    "updated_at": self.mod.dt.datetime.now(self.mod.dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                    "source": "google-search-console-ui-export",
                    "items": [{"landing": "/en/blog/example/", "locale": "en"}],
                }
            ),
            encoding="utf-8",
        )

        result = self.mod.validate_search_console_coverage(
            file_path=path,
            required_locales=["en"],
            max_age_hours=96,
            min_items_per_locale=1,
            expected_sources=self.mod.parse_expected_sources("google-search-console-api,google-search-console-ui-export"),
            allow_stub=False,
        )

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["counts"], {"en": 1})


if __name__ == "__main__":
    unittest.main()
