import importlib.util
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check-status-kpi-data.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("check_status_kpi_data", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StatusKpiDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        base_tmp = ROOT / ".tmp" / "unit-tests"
        base_tmp.mkdir(parents=True, exist_ok=True)
        self.tmp_dir = base_tmp / f"status-kpi-{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def write_search_console(self, items):
        path = self.tmp_dir / "search-console-keywords.json"
        path.write_text(
            json.dumps(
                {
                    "updated_at": "2026-06-16T16:43:49Z",
                    "source": "google-search-console-api",
                    "window": {"start_date": "2026-05-20", "end_date": "2026-06-16"},
                    "items": items,
                }
            ),
            encoding="utf-8",
        )
        return path

    def write_locale_kpi(self, rows):
        path = self.tmp_dir / "locale-kpi-tracker.csv"
        path.write_text(
            "date,domain,locale,owner,indexed_urls,discovered_urls,index_rate_pct,impressions,clicks,ctr_pct,avg_position,notes,next_action\n"
            + "\n".join(rows)
            + "\n",
            encoding="utf-8",
        )
        return path

    def test_valid_status_kpi_data_passes(self):
        search_path = self.write_search_console(
            [
                {
                    "query": "vram test",
                    "landing": "/de/tools/vram-calculator/",
                    "locale": "de",
                    "impressions": 6,
                    "clicks": 0,
                    "position": 38.83,
                }
            ]
        )
        kpi_path = self.write_locale_kpi(
            [
                "2026-06-16,localvram.com,de,seo-de,10,760,1.32,65,2,3.08,19.2,note,next",
                "2026-06-16,localvram.com,ko,seo-ko,14,760,1.84,78,1,1.28,15.77,note,next",
            ]
        )

        result = self.mod.validate_status_kpi_data(
            search_console_file=search_path,
            locale_kpi_file=kpi_path,
            expected_locales={"de", "ko"},
        )

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["search_rows"], 1)
        self.assertEqual(result["kpi_rows"], 2)

    def test_empty_status_sources_fail(self):
        search_path = self.write_search_console([])
        kpi_path = self.write_locale_kpi([])

        result = self.mod.validate_status_kpi_data(
            search_console_file=search_path,
            locale_kpi_file=kpi_path,
            expected_locales={"de"},
        )

        self.assertIn("Search Console needs at least 1 item(s) for /en/status/", result["errors"])
        self.assertIn("locale KPI needs at least one row for /en/status/", result["errors"])
        self.assertIn("locale KPI missing expected locales: de", result["errors"])

    def test_kpi_rejects_indexed_count_above_discovered_count(self):
        search_path = self.write_search_console(
            [
                {
                    "keyword": "vram",
                    "landing": "/de/",
                    "locale": "de",
                    "impressions": 1,
                    "clicks": 0,
                    "position": 10,
                }
            ]
        )
        kpi_path = self.write_locale_kpi(
            ["2026-06-16,localvram.com,de,seo-de,3,2,150,1,0,0,10,note,next"]
        )

        result = self.mod.validate_status_kpi_data(
            search_console_file=search_path,
            locale_kpi_file=kpi_path,
            expected_locales={"de"},
        )

        self.assertIn("locale KPI de indexed_urls cannot exceed discovered_urls", result["errors"])


if __name__ == "__main__":
    unittest.main()
