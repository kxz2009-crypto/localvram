import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DailyPipelineResilienceTests(unittest.TestCase):
    def test_daily_workflow_keeps_zh_stub_fallback_non_blocking(self):
        workflow = (ROOT / ".github" / "workflows" / "daily-content.yml").read_text(encoding="utf-8")

        self.assertIn("--fallback-mode stub", workflow)
        self.assertIn("scripts/check-cn-blog-sync.py --allow-stub", workflow)

    def test_quality_gate_does_not_hard_block_daily_on_dependent_pipeline_freshness(self):
        quality_gate = (ROOT / "scripts" / "quality-gate.py").read_text(encoding="utf-8")

        self.assertIn("--skip-home-sync-staleness", quality_gate)
        self.assertIn("check-cn-blog-sync.py", quality_gate)
        self.assertIn("--allow-stub", quality_gate)

    def test_cloudflare_worker_assets_directory_is_declared(self):
        config = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))

        self.assertEqual(config.get("name"), "localvram-site")
        self.assertEqual(config.get("assets", {}).get("directory"), "./dist")


if __name__ == "__main__":
    unittest.main()
