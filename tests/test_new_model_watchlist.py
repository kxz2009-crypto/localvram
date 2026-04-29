import datetime as dt
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


class NewModelWatchlistTests(unittest.TestCase):
    def test_recent_benchmark_becomes_high_priority_watchlist_item(self):
        radar = load_script("build-new-model-watchlist")
        now = dt.datetime(2026, 4, 29, 12, 0, tzinfo=dt.timezone.utc)
        benchmark = {
            "models": {
                "qwen3-coder:30b": {
                    "status": "ok",
                    "tokens_per_second": 122.5,
                    "latency_ms": 980,
                    "test_time": "2026-04-29T10:00:00Z",
                },
                "old-model:7b": {
                    "status": "ok",
                    "tokens_per_second": 90.0,
                    "latency_ms": 700,
                    "test_time": "2026-04-20T10:00:00Z",
                },
            }
        }
        catalog = {
            "items": [
                {
                    "ollama_tag": "qwen3-coder:30b",
                    "scenario": "coding",
                    "ollama_source_url": "https://ollama.com/library/qwen3-coder",
                }
            ]
        }

        items = radar.benchmark_candidates(
            benchmark,
            radar.catalog_by_tag(catalog),
            now=now,
            window_hours=48,
        )

        self.assertEqual([item["tag"] for item in items], ["qwen3-coder:30b"])
        self.assertEqual(items[0]["source"], "recent_benchmark")
        self.assertEqual(items[0]["status"], "measured")
        self.assertGreaterEqual(items[0]["priority_score"], 90)
        self.assertIn("rtx 3090 ollama benchmark", items[0]["keyword"])
        self.assertEqual(items[0]["ollama_command"], "ollama run qwen3-coder:30b")

    def test_build_watchlist_merges_weekly_targets_and_recent_measurements(self):
        radar = load_script("build-new-model-watchlist")
        now = dt.datetime(2026, 4, 29, 12, 0, tzinfo=dt.timezone.utc)
        catalog_index = radar.catalog_by_tag({"items": [{"ollama_tag": "gpt-oss:20b", "scenario": "reasoning"}]})
        items = radar.benchmark_candidates(
            {
                "models": {
                    "gpt-oss:20b": {
                        "status": "ok",
                        "tokens_per_second": 156.0,
                        "latency_ms": 1524,
                        "test_time": "2026-04-29T11:00:00Z",
                    }
                }
            },
            catalog_index,
            now=now,
            window_hours=48,
        )
        items.extend(
            radar.weekly_plan_candidates(
                {"added_targets": ["qwen3.6:30b"]},
                catalog_index,
                now=now,
            )
        )
        ranked = radar.dedupe_rank(items, limit=10)

        tags = [item["tag"] for item in ranked]
        self.assertIn("gpt-oss:20b", tags)
        self.assertIn("qwen3.6:30b", tags)
        self.assertEqual(ranked[0]["tag"], "gpt-oss:20b")


if __name__ == "__main__":
    unittest.main()
