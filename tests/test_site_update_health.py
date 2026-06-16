import importlib.util
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check-site-update-health.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("check_site_update_health", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SiteUpdateHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        base_tmp = ROOT / ".tmp" / "unit-tests"
        base_tmp.mkdir(parents=True, exist_ok=True)
        self.tmp_dir = base_tmp / f"site-update-health-{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def write_json(self, name, payload):
        path = self.tmp_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def test_passes_when_home_sync_and_daily_publish_are_fresh(self):
        status = self.write_json("status.json", {"last_hardware_sync": "2026-04-24T05:43:44Z"})
        publish_log = self.write_json(
            "content-publish-log.json",
            {
                "updated_at": "2026-04-26T04:03:11Z",
                "last_run": {
                    "queue_date": "2026-04-26",
                    "published_count": 1,
                    "published": [
                        {
                            "slug": "daily-local-llm-benchmark-snapshot-2026-04-26",
                            "out_file": str(self.tmp_dir / "daily-local-llm-benchmark-snapshot-2026-04-26.md"),
                        }
                    ],
                },
            },
        )
        updates = self.write_json(
            "daily-updates.json",
            {"items": [{"date": "2026-04-26", "published_posts": [{"slug": "daily-local-llm-benchmark-snapshot-2026-04-26"}]}]},
        )
        (self.tmp_dir / "daily-local-llm-benchmark-snapshot-2026-04-26.md").write_text("---\ntitle: ok\n---\n", encoding="utf-8")

        report = self.mod.check_site_update_health(
            now_utc=self.mod.parse_iso_utc("2026-04-27T15:00:00Z"),
            status_file=status,
            content_publish_file=publish_log,
            daily_updates_file=updates,
            root_dir=self.tmp_dir,
        )

        self.assertEqual(report["result"], "ok")
        self.assertEqual(report["errors"], [])

    def test_fails_when_home_sync_is_stale_or_daily_publish_is_missing(self):
        status = self.write_json("status.json", {"last_hardware_sync": "2026-04-18T00:00:00Z"})
        publish_log = self.write_json(
            "content-publish-log.json",
            {
                "updated_at": "2026-04-20T00:00:00Z",
                "last_run": {
                    "queue_date": "2026-04-20",
                    "published_count": 0,
                    "published": [],
                },
            },
        )
        updates = self.write_json("daily-updates.json", {"items": [{"date": "2026-04-20", "published_posts": []}]})

        report = self.mod.check_site_update_health(
            now_utc=self.mod.parse_iso_utc("2026-04-27T15:00:00Z"),
            status_file=status,
            content_publish_file=publish_log,
            daily_updates_file=updates,
            root_dir=self.tmp_dir,
            max_home_sync_age_hours=192,
            max_daily_publish_age_hours=48,
        )

        self.assertEqual(report["result"], "failed")
        self.assertIn("home_sync_stale(age_hours=231.0, max_hours=192)", report["errors"])
        self.assertIn("daily_publish_stale(age_hours=183.0, max_hours=48)", report["errors"])
        self.assertIn("daily_publish_zero_published(queue_date=2026-04-20)", report["errors"])


if __name__ == "__main__":
    unittest.main()
