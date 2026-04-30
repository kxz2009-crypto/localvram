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
    def test_parse_ollama_library_updated_age(self):
        radar = load_script("build-new-model-watchlist")

        fresh = radar.parse_ollama_library_page(
            "qwen3.6",
            "<main><span>644.1K Downloads</span><span>Updated 1 week ago</span></main>",
        )
        stale = radar.parse_ollama_library_page(
            "deepseek-r1",
            "<main><span>67.8M Downloads</span><span>Updated 10 months ago</span></main>",
        )

        self.assertEqual(fresh["updated_days"], 7)
        self.assertEqual(fresh["downloads"], "644.1K")
        self.assertEqual(stale["updated_days"], 300)

    def test_recent_benchmark_only_counts_for_new_model_families(self):
        radar = load_script("build-new-model-watchlist")
        now = dt.datetime(2026, 4, 29, 12, 0, tzinfo=dt.timezone.utc)
        benchmark = {
            "models": {
                "qwen3.6:35b": {
                    "status": "ok",
                    "tokens_per_second": 122.5,
                    "latency_ms": 980,
                    "test_time": "2026-04-29T10:00:00Z",
                },
                "deepseek-r1:14b": {
                    "status": "ok",
                    "tokens_per_second": 90.0,
                    "latency_ms": 700,
                    "test_time": "2026-04-29T10:00:00Z",
                },
            }
        }
        catalog = {
            "items": [
                {
                    "ollama_tag": "qwen3.6:35b",
                    "scenario": "coding",
                    "ollama_source_url": "https://ollama.com/library/qwen3.6",
                }
            ]
        }

        items = radar.benchmark_candidates(
            benchmark,
            radar.catalog_by_tag(catalog),
            local_inventory={"families": {"qwen3.6"}, "tags": {"qwen3.6:35b"}, "model_count": 44},
            now=now,
            window_hours=48,
        )

        self.assertEqual([item["tag"] for item in items], ["qwen3.6:35b"])
        self.assertEqual(items[0]["source"], "new_family_benchmark")
        self.assertEqual(items[0]["status"], "measured")
        self.assertGreaterEqual(items[0]["priority_score"], 90)
        self.assertIn("rtx 3090 ollama benchmark", items[0]["keyword"])
        self.assertEqual(items[0]["ollama_command"], "ollama run qwen3.6:35b")
        self.assertEqual(items[0]["local_inventory_status"]["status"], "downloaded")
        self.assertEqual(items[0]["benchmark_status"]["status"], "measured")
        self.assertEqual(items[0]["ollama_library_freshness"]["status"], "inferred")
        self.assertEqual(items[0]["traffic_priority"], "publish_now")

    def test_stale_ollama_library_age_blocks_priority_family(self):
        radar = load_script("build-new-model-watchlist")
        now = dt.datetime(2026, 4, 29, 12, 0, tzinfo=dt.timezone.utc)
        benchmark = {
            "models": {
                "qwen3.6:35b": {
                    "status": "ok",
                    "tokens_per_second": 122.5,
                    "latency_ms": 980,
                    "test_time": "2026-04-29T10:00:00Z",
                }
            }
        }

        items = radar.benchmark_candidates(
            benchmark,
            {},
            {"qwen3.6": {"updated_label": "3 months ago", "updated_days": 90, "tag_ages": {}}},
            {},
            now=now,
            window_hours=48,
            max_library_age_days=14,
        )

        self.assertEqual(items, [])

    def test_build_watchlist_merges_weekly_targets_and_recent_measurements(self):
        radar = load_script("build-new-model-watchlist")
        now = dt.datetime(2026, 4, 29, 12, 0, tzinfo=dt.timezone.utc)
        catalog = {
            "items": [
                {"ollama_tag": "gpt-oss:20b", "library_id": "gpt-oss", "scenario": "reasoning", "params_b": 20},
                {"ollama_tag": "qwen3.6:35b", "library_id": "qwen3.6", "scenario": "reasoning", "params_b": 35},
                {"ollama_tag": "deepseek-r1:14b", "library_id": "deepseek-r1", "scenario": "reasoning", "params_b": 14},
            ]
        }
        catalog_index = radar.catalog_by_tag(catalog)
        catalog_family_index = radar.catalog_by_family(catalog)
        benchmark = {
            "models": {
                "gpt-oss:20b": {
                    "status": "ok",
                    "tokens_per_second": 156.0,
                    "latency_ms": 1524,
                    "test_time": "2026-04-29T11:00:00Z",
                },
                "deepseek-r1:14b": {
                    "status": "ok",
                    "tokens_per_second": 90.0,
                    "latency_ms": 900,
                    "test_time": "2026-04-29T11:00:00Z",
                },
            }
        }
        items = radar.benchmark_candidates(
            benchmark,
            catalog_index,
            {"gpt-oss": {"updated_label": "2 days ago", "updated_days": 2, "tag_ages": {}}, "deepseek-r1": {"updated_label": "10 months ago", "updated_days": 300, "tag_ages": {}}},
            {"families": {"gpt-oss", "qwen3.6"}, "tags": {"gpt-oss:20b", "qwen3.6:35b"}, "model_count": 44},
            now=now,
            window_hours=48,
        )
        items.extend(
            radar.weekly_plan_candidates(
                {"priority_families": ["qwen3.6", "deepseek-r1"]},
                catalog_index,
                catalog_family_index,
                benchmark,
                {"qwen3.6": {"updated_label": "1 week ago", "updated_days": 7, "tag_ages": {}}, "deepseek-r1": {"updated_label": "10 months ago", "updated_days": 300, "tag_ages": {}}},
                {"families": {"gpt-oss", "qwen3.6"}, "tags": {"gpt-oss:20b", "qwen3.6:35b"}, "model_count": 44},
                now=now,
            )
        )
        ranked = radar.dedupe_rank(items, limit=10)

        tags = [item["tag"] for item in ranked]
        self.assertIn("gpt-oss:20b", tags)
        self.assertIn("qwen3.6:35b", tags)
        self.assertNotIn("deepseek-r1:14b", tags)
        self.assertIn(ranked[0]["tag"], {"gpt-oss:20b", "qwen3.6:35b"})

    def test_local_inventory_index_reads_runner_status_and_weekly_plan(self):
        radar = load_script("build-new-model-watchlist")

        inventory = radar.build_local_inventory_index(
            {"local_models_sample": ["qwen3.6:35b"], "local_families": ["gemma4"], "local_model_count": 2},
            {
                "api": {"tags": {"model_count": 44, "sample": ["gpt-oss:20b"]}},
                "summary": {"required_targets_runnable": ["ministral-3"]},
            },
        )

        self.assertIn("qwen3.6:35b", inventory["tags"])
        self.assertIn("gpt-oss:20b", inventory["tags"])
        self.assertIn("gemma4", inventory["families"])
        self.assertIn("ministral-3", inventory["families"])
        self.assertEqual(inventory["model_count"], 44)

    def test_ollama_freshness_status_marks_unknown_as_inferred(self):
        radar = load_script("build-new-model-watchlist")

        self.assertEqual(radar.ollama_freshness_status({}, 14), "inferred")
        self.assertEqual(radar.ollama_freshness_status({"updated_days": 7}, 14), "fresh")
        self.assertEqual(radar.ollama_freshness_status({"updated_days": 90}, 14), "stale")


if __name__ == "__main__":
    unittest.main()
