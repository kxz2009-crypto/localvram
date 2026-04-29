import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_script(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContentStrategyTests(unittest.TestCase):
    def test_daily_fallback_is_model_pick_not_thin_snapshot(self):
        publish = load_script("publish-content-queue")
        content = publish.build_daily_fallback_content(
            "2026-04-29",
            [
                {
                    "tag": "qwen3-coder:30b",
                    "tokens_per_second": 160.0,
                    "latency_ms": 835.0,
                    "test_time": "2026-04-29T05:39:58Z",
                },
                {
                    "tag": "qwen3:8b",
                    "tokens_per_second": 135.3,
                    "latency_ms": 1270.0,
                    "test_time": "2026-04-29T05:39:58Z",
                },
            ],
        )

        self.assertIn("Today's Local LLM Pick", content["title"])
        self.assertIn("qwen3-coder:30b", content["title"])
        self.assertNotIn("Daily Local LLM Benchmark Snapshot", content["title"])
        self.assertIn("Who should try it", content["body"])
        self.assertIn("24-48 hour traffic window", content["body"])
        self.assertIn("ollama run qwen3-coder:30b", content["body"])

    def test_draft_template_targets_new_model_search_window(self):
        agent = load_script("daily-content-agent")
        body = agent.draft_markdown(
            title="Qwen3 Coder 30B on RTX 3090: Ollama Benchmark, VRAM, and Setup",
            keyword="qwen3-coder:30b rtx 3090 ollama benchmark",
            score_value=900,
            source="benchmark_fallback",
            measured=[
                {
                    "tag": "qwen3-coder:30b",
                    "tokens_per_second": 160.0,
                    "latency_ms": 835.0,
                    "test_time": "2026-04-29T05:39:58Z",
                }
            ],
            links={"runpod": "/go/runpod", "vast": "/go/vast"},
            landing="/en/models/",
            date_iso="2026-04-29",
        )

        self.assertIn("ollama run qwen3-coder:30b", body)
        self.assertIn("first 24-48 hours after an Ollama model appears", body)
        self.assertIn("RTX 3090 decision matrix", body)
        self.assertIn("Who should skip it", body)

    def test_watchlist_item_becomes_high_score_daily_candidate(self):
        agent = load_script("daily-content-agent")
        candidate = agent.candidate_from_new_model_watchlist(
            {
                "tag": "gpt-oss:20b",
                "keyword": "gpt-oss:20b rtx 3090 ollama benchmark",
                "slug": "model-gpt-oss-20b-rtx-3090-ollama-benchmark",
                "landing": "/en/models/gpt-oss-20b/",
                "priority_score": 96,
            }
        )

        self.assertEqual(candidate["source"], "new_model_watchlist")
        self.assertEqual(candidate["landing"], "/en/models/gpt-oss-20b/")
        self.assertEqual(candidate["tag"], "gpt-oss:20b")
        self.assertGreaterEqual(agent.score_with_boost(candidate), 900)


if __name__ == "__main__":
    unittest.main()
