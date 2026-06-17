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
        measured = [
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
        ]
        expected_pick = publish.pick_today_model(measured, queue_date="2026-04-29")["tag"]
        content = publish.build_daily_fallback_content(
            "2026-04-29",
            measured,
        )
        expected_landing = publish.model_landing_from_tag(expected_pick, "/en/models/")

        self.assertIn("Today's Local LLM Pick", content["title"])
        self.assertIn(expected_pick, content["title"])
        self.assertNotIn("Daily Local LLM Benchmark Snapshot", content["title"])
        self.assertIn("Who should try it", content["body"])
        self.assertIn("traffic window", content["body"])
        self.assertIn(f"ollama run {expected_pick}", content["body"])
        self.assertIn(f"Model page: {expected_landing}", content["body"])

    def test_publish_fallback_model_landing_prefers_catalog_q4_page(self):
        publish = load_script("publish-content-queue")

        landing = publish.model_landing_from_tag("qwen3-coder:30b", "/en/models/")

        self.assertEqual(landing, "/en/models/qwen3-coder-30b-q4/")

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
            traffic_priority="publish_now",
            ollama_updated_label="2 days ago",
            local_inventory_status="downloaded",
            benchmark_status="measured",
            benchmark_measured_at="2026-04-29T05:39:58Z",
        )

        self.assertIn("ollama run qwen3-coder:30b", body)
        self.assertIn("first 24-48 hours after an Ollama model appears", body)
        self.assertIn("RTX 3090 decision matrix", body)
        self.assertIn("Who should skip it", body)
        self.assertIn("## Evidence snapshot", body)
        self.assertIn("## Editorial angle", body)
        self.assertIn("Ollama freshness: 2 days ago", body)
        self.assertIn("Local inventory: downloaded", body)
        self.assertIn("RTX 3090 benchmark: measured", body)
        self.assertIn("Content angle:", body)
        self.assertIn("Model page: /en/models/qwen3-coder-30b-q4/", body)
        self.assertIn("Topic hub: /en/guides/best-coding-models/", body)
        self.assertIn("Latest verified data: /en/status/data-freshness/", body)
        self.assertIn('content_angle: "', body)
        self.assertIn('traffic_priority: "publish_now"', body)

    def test_model_landing_from_tag_prefers_catalog_q4_page(self):
        agent = load_script("daily-content-agent")

        landing = agent.model_landing_from_tag("qwen3-coder:30b", "/en/models/")

        self.assertEqual(landing, "/en/models/qwen3-coder-30b-q4/")

    def test_quality_floor_candidates_keep_daily_content_specific(self):
        agent = load_script("daily-content-agent")

        candidates = agent.build_quality_floor_candidates(
            [
                {
                    "tag": "qwen3-coder:30b",
                    "tokens_per_second": 160.0,
                    "latency_ms": 835.0,
                    "test_time": "2026-04-29T05:39:58Z",
                }
            ],
            "2026-04-29",
            max_count=1,
        )

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate["source"], "quality_floor_fallback")
        self.assertEqual(candidate["model_tag"], "qwen3-coder:30b")
        self.assertEqual(candidate["benchmark_status"], "measured")
        self.assertEqual(candidate["traffic_priority"], "fallback")
        self.assertEqual(candidate["model_key"], "")
        self.assertIn("qwen3-coder-30b", candidate["slug"])
        self.assertIn(candidate["content_angle"], candidate["slug"])
        self.assertGreaterEqual(agent.score_with_boost(candidate), 120)

    def test_watchlist_item_becomes_high_score_daily_candidate(self):
        agent = load_script("daily-content-agent")
        candidate = agent.candidate_from_new_model_watchlist(
            {
                "tag": "gpt-oss:20b",
                "keyword": "gpt-oss:20b rtx 3090 ollama benchmark",
                "slug": "model-gpt-oss-20b-rtx-3090-ollama-benchmark",
                "landing": "/en/models/gpt-oss-20b/",
                "priority_score": 96,
                "traffic_priority": "publish_now",
                "ollama_updated_label": "1 day ago",
                "local_inventory_status": {"status": "downloaded"},
                "benchmark_status": {"status": "measured", "measured_at": "2026-04-29T05:39:58Z"},
            }
        )

        self.assertEqual(candidate["source"], "new_model_watchlist")
        self.assertEqual(candidate["landing"], "/en/models/gpt-oss-20b/")
        self.assertEqual(candidate["tag"], "gpt-oss:20b")
        self.assertEqual(candidate["model_key"], "gpt-oss-20b")
        self.assertEqual(candidate["traffic_priority"], "publish_now")
        self.assertEqual(candidate["ollama_updated_label"], "1 day ago")
        self.assertEqual(candidate["local_inventory_status"], "downloaded")
        self.assertEqual(candidate["benchmark_status"], "measured")
        self.assertEqual(candidate["benchmark_measured_at"], "2026-04-29T05:39:58Z")
        self.assertGreaterEqual(agent.score_with_boost(candidate), 5900)

    def test_traffic_priority_drives_daily_candidate_order(self):
        agent = load_script("daily-content-agent")
        publish_now = {
            "slug": "new-model",
            "keyword": "new model rtx 3090 benchmark",
            "search_intent_score": 8,
            "commercial_intent_score": 8,
            "freshness_gap_score": 8,
            "traffic_priority": "publish_now",
        }
        ordinary = {
            "slug": "ordinary",
            "keyword": "ordinary guide",
            "search_intent_score": 10,
            "commercial_intent_score": 10,
            "freshness_gap_score": 10,
        }
        backlog = {
            "slug": "backlog",
            "keyword": "backlog model",
            "search_intent_score": 10,
            "commercial_intent_score": 10,
            "freshness_gap_score": 10,
            "traffic_priority": "backlog",
        }

        selected = agent.filter_fresh_candidates(
            [ordinary, publish_now, backlog],
            blocked_slugs=set(),
            blocked_topics=set(),
            min_score=120,
        )

        self.assertEqual([item["slug"] for item in selected], ["new-model", "ordinary"])

    def test_new_model_candidates_respect_model_cooldown(self):
        agent = load_script("daily-content-agent")
        first = agent.candidate_from_new_model_watchlist(
            {
                "tag": "qwen3.6:35b",
                "keyword": "qwen3.6:35b rtx 3090 ollama benchmark",
                "slug": "model-qwen3-6-35b-rtx-3090-ollama-benchmark",
                "priority_score": 100,
            }
        )
        second = agent.candidate_from_new_model_watchlist(
            {
                "tag": "gpt-oss:20b",
                "keyword": "gpt-oss:20b rtx 3090 ollama benchmark",
                "slug": "model-gpt-oss-20b-rtx-3090-ollama-benchmark",
                "priority_score": 96,
            }
        )

        selected = agent.filter_fresh_candidates(
            [first, second],
            blocked_slugs=set(),
            blocked_topics=set(),
            blocked_model_keys={"qwen3-6-35b"},
            min_score=120,
        )

        self.assertEqual([item["tag"] for item in selected], ["gpt-oss:20b"])

    def test_title_humanizer_preserves_local_llm_acronyms(self):
        agent = load_script("daily-content-agent")

        title = agent.build_title("qwen3:14b rtx 3090 ollama vram benchmark", "2026-04-29")

        self.assertIn("RTX 3090", title)
        self.assertIn("VRAM", title)
        self.assertNotIn("Rtx", title)
        self.assertNotIn("Vram", title)


if __name__ == "__main__":
    unittest.main()
