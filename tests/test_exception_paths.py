import importlib.util
import io
import subprocess
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

RUNNER_MODULE_PATH = SCRIPTS_DIR / "runner-diagnostics.py"
WEEKLY_MODULE_PATH = SCRIPTS_DIR / "weekly-benchmark.py"
PREFLIGHT_MODULE_PATH = SCRIPTS_DIR / "ollama-preflight.py"
PUBLISH_WRAPPER_MODULE_PATH = SCRIPTS_DIR / "run-publish-workflow.py"
WEEKLY_WRAPPER_MODULE_PATH = SCRIPTS_DIR / "run-weekly-publish-pipeline.py"
DAILY_WRAPPER_MODULE_PATH = SCRIPTS_DIR / "run-daily-content-workflow.py"
OPS_REVIEW_MODULE_PATH = SCRIPTS_DIR / "ops-review.py"
CLUSTER_BENCHMARK_MODULE_PATH = SCRIPTS_DIR / "cluster-benchmark.py"
APPLY_I18N_PACK_MODULE_PATH = SCRIPTS_DIR / "apply-i18n-translation-pack.py"
GSC_COVERAGE_MODULE_PATH = SCRIPTS_DIR / "check-search-console-coverage.py"
BAIDU_PUSH_MODULE_PATH = SCRIPTS_DIR / "push-baidu-urls.py"
PRUNE_RETIRED_MODULE_PATH = SCRIPTS_DIR / "prune-retired-benchmark-data.py"
REFRESH_OPPORTUNITIES_MODULE_PATH = SCRIPTS_DIR / "refresh-content-opportunities.py"
REVIEW_COMMUNITY_MODULE_PATH = SCRIPTS_DIR / "review-community-submissions.py"
APPLY_I18N_WAVE_MODULE_PATH = SCRIPTS_DIR / "apply-i18n-wave.py"
REVIEW_CONTENT_QUEUE_MODULE_PATH = SCRIPTS_DIR / "review-content-queue.py"
CONVERSION_FUNNEL_MODULE_PATH = SCRIPTS_DIR / "build-conversion-funnel.py"
SUBMISSION_REVIEW_MODULE_PATH = SCRIPTS_DIR / "build-submission-review.py"
I18N_READINESS_MODULE_PATH = SCRIPTS_DIR / "i18n-readiness.py"
UPDATE_PIPELINE_STATUS_MODULE_PATH = SCRIPTS_DIR / "update-pipeline-status.py"
SCORE_SUBMISSION_MODULE_PATH = SCRIPTS_DIR / "score-user-submission.py"
RETIREMENT_CANDIDATES_MODULE_PATH = SCRIPTS_DIR / "generate-retirement-candidates.py"
REVIEW_RETIREMENT_MODULE_PATH = SCRIPTS_DIR / "review-retirement-candidates.py"
REFRESH_AFFILIATE_FUNNEL_MODULE_PATH = SCRIPTS_DIR / "refresh-affiliate-funnel.py"


def load_module(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExceptionPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_module("runner_diagnostics", RUNNER_MODULE_PATH)
        cls.weekly = load_module("weekly_benchmark", WEEKLY_MODULE_PATH)
        cls.preflight = load_module("ollama_preflight", PREFLIGHT_MODULE_PATH)
        cls.publish_wrapper = load_module("run_publish_workflow", PUBLISH_WRAPPER_MODULE_PATH)
        cls.weekly_wrapper = load_module("run_weekly_publish_pipeline", WEEKLY_WRAPPER_MODULE_PATH)
        cls.daily_wrapper = load_module("run_daily_content_workflow", DAILY_WRAPPER_MODULE_PATH)
        cls.ops_review = load_module("ops_review", OPS_REVIEW_MODULE_PATH)
        cls.cluster_benchmark = load_module("cluster_benchmark", CLUSTER_BENCHMARK_MODULE_PATH)
        cls.apply_i18n_pack = load_module("apply_i18n_translation_pack", APPLY_I18N_PACK_MODULE_PATH)
        cls.gsc_coverage = load_module("check_search_console_coverage", GSC_COVERAGE_MODULE_PATH)
        cls.baidu_push = load_module("push_baidu_urls", BAIDU_PUSH_MODULE_PATH)
        cls.prune_retired = load_module("prune_retired_benchmark_data", PRUNE_RETIRED_MODULE_PATH)
        cls.refresh_opps = load_module("refresh_content_opportunities", REFRESH_OPPORTUNITIES_MODULE_PATH)
        cls.review_community = load_module("review_community_submissions", REVIEW_COMMUNITY_MODULE_PATH)
        cls.apply_wave = load_module("apply_i18n_wave", APPLY_I18N_WAVE_MODULE_PATH)
        cls.review_queue = load_module("review_content_queue", REVIEW_CONTENT_QUEUE_MODULE_PATH)
        cls.conversion_funnel = load_module("build_conversion_funnel", CONVERSION_FUNNEL_MODULE_PATH)
        cls.submission_review = load_module("build_submission_review", SUBMISSION_REVIEW_MODULE_PATH)
        cls.i18n_readiness = load_module("i18n_readiness", I18N_READINESS_MODULE_PATH)
        cls.update_pipeline_status = load_module("update_pipeline_status", UPDATE_PIPELINE_STATUS_MODULE_PATH)
        cls.score_submission = load_module("score_user_submission", SCORE_SUBMISSION_MODULE_PATH)
        cls.retirement_candidates = load_module("generate_retirement_candidates", RETIREMENT_CANDIDATES_MODULE_PATH)
        cls.review_retirement = load_module("review_retirement_candidates", REVIEW_RETIREMENT_MODULE_PATH)
        cls.refresh_affiliate = load_module("refresh_affiliate_funnel", REFRESH_AFFILIATE_FUNNEL_MODULE_PATH)

    def test_runner_run_cmd_exception(self):
        with patch.object(self.runner.subprocess, "run", side_effect=RuntimeError("boom")):
            code, out, err = self.runner.run_cmd(["echo", "ok"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("boom", err)

    def test_weekly_run_cmd_exception(self):
        with patch.object(self.weekly.subprocess, "run", side_effect=RuntimeError("boom")):
            code, out, err = self.weekly.run_cmd(["echo", "ok"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("boom", err)

    def test_weekly_api_request_http_error(self):
        http_error = urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/version",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"bad request"}'),
        )
        with patch.object(self.weekly.urllib.request, "urlopen", side_effect=http_error):
            with self.assertRaises(RuntimeError) as ctx:
                self.weekly.api_request("http://127.0.0.1:11434", "/api/version", retry_delays=[])
        self.assertIn("HTTP 400", str(ctx.exception))
        self.assertIn("bad request", str(ctx.exception))

    def test_weekly_api_request_timeout_retry_exhausted(self):
        with (
            patch.object(self.weekly.urllib.request, "urlopen", side_effect=TimeoutError("late response")),
            patch.object(self.weekly.time, "sleep") as sleep_mock,
        ):
            with self.assertRaises(RuntimeError) as ctx:
                self.weekly.api_request(
                    "http://127.0.0.1:11434",
                    "/api/version",
                    retry_delays=[0.0, 0.0],
                )
        self.assertIn("request timed out", str(ctx.exception))
        self.assertEqual(sleep_mock.call_count, 2)

    def test_runner_fetch_json_retry_exhausted(self):
        with (
            patch.object(self.runner.urllib.request, "urlopen", side_effect=urllib.error.URLError("down")),
            patch.object(self.runner.time, "sleep") as sleep_mock,
        ):
            with self.assertRaises(urllib.error.URLError):
                self.runner.fetch_json(
                    "http://127.0.0.1:11434",
                    "/api/version",
                    timeout=1,
                    retry_delays=[0.0, 0.0],
                )
        self.assertEqual(sleep_mock.call_count, 2)

    def test_preflight_run_cmd_exception(self):
        with patch.object(self.preflight.subprocess, "run", side_effect=RuntimeError("boom")):
            code, out, err = self.preflight.run_cmd(["echo", "ok"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("boom", err)

    def test_preflight_fetch_local_models_with_retry_exhausted(self):
        with (
            patch.object(self.preflight, "fetch_local_models", side_effect=urllib.error.URLError("down")),
            patch.object(self.preflight.time, "sleep") as sleep_mock,
        ):
            with self.assertRaises(urllib.error.URLError):
                self.preflight.fetch_local_models_with_retry(
                    "http://127.0.0.1:11434",
                    retry_delays=[0.0, 0.0],
                )
        self.assertEqual(sleep_mock.call_count, 2)

    def test_preflight_emit_failure_class_stdout_contract(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.preflight.emit_failure_class("model_missing", "no runnable models")
        output = stdout.getvalue()
        self.assertIn("failure_class=model_missing", output)
        self.assertIn("failure_detail=no runnable models", output)
        self.assertIn("::error title=FailureClass::model_missing - no runnable models", output)

    def test_preflight_emit_failure_class_contract_toggle(self):
        stdout = io.StringIO()
        with patch.dict("os.environ", {"LV_STDOUT_CONTRACT": "false"}, clear=False):
            with redirect_stdout(stdout):
                self.preflight.emit_failure_class("model_missing", "no runnable models")
        self.assertEqual(stdout.getvalue(), "")

    def test_weekly_emit_failure_class_contract_toggle(self):
        stdout = io.StringIO()
        with patch.dict("os.environ", {"LV_STDOUT_CONTRACT": "false"}, clear=False):
            with redirect_stdout(stdout):
                self.weekly.emit_failure_class("benchmark_threshold_not_met", "insufficient runs")
        self.assertEqual(stdout.getvalue(), "")

    def test_publish_wrapper_run_gh_retry(self):
        calls = [
            subprocess.CompletedProcess(args=["gh", "api"], returncode=1, stdout="", stderr="timed out"),
            subprocess.CompletedProcess(args=["gh", "api"], returncode=0, stdout="ok", stderr=""),
        ]
        with (
            patch.object(self.publish_wrapper.subprocess, "run", side_effect=calls) as run_mock,
            patch.object(self.publish_wrapper.time, "sleep") as sleep_mock,
        ):
            result = self.publish_wrapper._run_gh("gh", ["api"], retry_delays=[0], allow_retry=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(run_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_count, 1)

    def test_weekly_wrapper_run_gh_retry(self):
        calls = [
            subprocess.CompletedProcess(args=["gh", "api"], returncode=1, stdout="", stderr="timeout"),
            subprocess.CompletedProcess(args=["gh", "api"], returncode=0, stdout="ok", stderr=""),
        ]
        with (
            patch.object(self.weekly_wrapper.subprocess, "run", side_effect=calls) as run_mock,
            patch.object(self.weekly_wrapper.time, "sleep") as sleep_mock,
        ):
            result = self.weekly_wrapper.run_gh("gh", ["api"], retry_delays=[0], allow_retry=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(run_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_count, 1)

    def test_weekly_wrapper_parse_run_id(self):
        run_id = self.weekly_wrapper.parse_run_id_from_stdout(
            "Created workflow_dispatch event for https://github.com/example/repo/actions/runs/123456789"
        )
        self.assertEqual(run_id, 123456789)

    def test_daily_wrapper_run_gh_retry(self):
        calls = [
            subprocess.CompletedProcess(args=["gh", "api"], returncode=1, stdout="", stderr="timed out"),
            subprocess.CompletedProcess(args=["gh", "api"], returncode=0, stdout="ok", stderr=""),
        ]
        with (
            patch.object(self.daily_wrapper.subprocess, "run", side_effect=calls) as run_mock,
            patch.object(self.daily_wrapper.time, "sleep") as sleep_mock,
        ):
            result = self.daily_wrapper.run_gh("gh", ["api"], retry_delays=[0], allow_retry=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(run_mock.call_count, 2)
        self.assertEqual(sleep_mock.call_count, 1)

    def test_daily_wrapper_parse_run_id(self):
        run_id = self.daily_wrapper.parse_run_id_from_stdout(
            "Dispatched: https://github.com/example/repo/actions/runs/99887766"
        )
        self.assertEqual(run_id, 99887766)

    def test_ops_review_parse_updated_paths(self):
        stdout = "updated=src\\data\\foo.json status=ok\nupdated=src/data/foo.json status=ok\nupdated=src/data/bar.json"
        paths = self.ops_review.parse_updated_paths(stdout)
        self.assertEqual(paths, ["src/data/foo.json", "src/data/bar.json"])

    def test_ops_review_run_script_missing(self):
        with self.assertRaises(SystemExit) as ctx:
            self.ops_review.run_script("no-such-script.py", [], "missing")
        self.assertIn("missing script:", str(ctx.exception))

    def test_cluster_run_cmd_exception(self):
        with patch.object(self.cluster_benchmark.subprocess, "run", side_effect=RuntimeError("boom")):
            code, out, err = self.cluster_benchmark.run_cmd(["echo", "ok"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("boom", err)

    def test_apply_i18n_load_phrase_map(self):
        map_data = {"translations": {"hello": "bonjour"}}
        self.assertEqual(self.apply_i18n_pack.load_phrase_map(map_data), {"hello": "bonjour"})
        list_data = {"phrases": [{"en": "hello", "translation": "hola"}]}
        self.assertEqual(self.apply_i18n_pack.load_phrase_map(list_data), {"hello": "hola"})

    def test_gsc_parse_helpers(self):
        locales = self.gsc_coverage.parse_locales("en,ES,xx,pt, invalid")
        self.assertEqual(locales, ["en", "es", "xx", "pt"])
        parsed = self.gsc_coverage.parse_iso_utc("2026-03-01T10:00:00Z")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.tzinfo, self.gsc_coverage.dt.timezone.utc)

    def test_baidu_parse_sitemap(self):
        xml_text = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>https://localvram.cn/a</loc></url>"
            "<url><loc>https://localvram.cn/b</loc></url>"
            "</urlset>"
        )
        urls = self.baidu_push.parse_sitemap(xml_text)
        self.assertEqual(urls, ["https://localvram.cn/a", "https://localvram.cn/b"])

    def test_prune_is_retired_model_ref(self):
        retired_families = {"qwen3"}
        retired_tags = {"llama3.3:70b"}
        aliases = {"qwen3:8b-q4_k_m": "qwen3:8b"}
        self.assertTrue(
            self.prune_retired.is_retired_model_ref("qwen3:8b-q4_k_m", retired_families, retired_tags, aliases)
        )
        self.assertTrue(
            self.prune_retired.is_retired_model_ref("llama3.3:70b-instruct-q4", retired_families, retired_tags, aliases)
        )
        self.assertFalse(
            self.prune_retired.is_retired_model_ref("mistral:7b", retired_families, retired_tags, aliases)
        )

    def test_refresh_helpers(self):
        self.assertEqual(self.refresh_opps.slugify("Hello, World!"), "hello-world")
        self.assertEqual(self.refresh_opps.clamp(15, 1, 10), 10)
        score = self.refresh_opps.item_score(
            {"search_intent_score": 4, "commercial_intent_score": 5, "freshness_gap_score": 6}
        )
        self.assertEqual(score, 120)

    def test_review_community_normalize_ids(self):
        values = self.review_community.normalize_ids("id1, id2,id1,, id3")
        self.assertEqual(values, ["id1", "id2", "id3"])

    def test_apply_wave_detect_locale(self):
        path = ROOT / "tmp-i18n-template-fr.json"
        path.write_text('{"locale":"fr"}', encoding="utf-8")
        try:
            self.assertEqual(self.apply_wave.detect_locale(path), "fr")
        finally:
            path.unlink(missing_ok=True)

    def test_review_queue_helpers(self):
        self.assertEqual(self.review_queue.slugify("Hello GPT-5"), "hello-gpt-5")
        tokens = self.review_queue.normalize_topic_text("the best local llm guide")
        self.assertIn("best", tokens)
        self.assertNotIn("the", tokens)

    def test_conversion_funnel_helpers(self):
        self.assertEqual(self.conversion_funnel.safe_path_from_url("https://localvram.com/en/models/qwen3"), "/en/models/qwen3")
        self.assertEqual(self.conversion_funnel.safe_path_from_url(""), "")
        self.assertEqual(self.conversion_funnel.percent(25, 100), 25.0)

    def test_submission_review_parse_iso_utc(self):
        parsed = self.submission_review.parse_iso_utc("2026-03-01T12:00:00Z")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.tzinfo, self.submission_review.dt.timezone.utc)
        self.assertIsNone(self.submission_review.parse_iso_utc("invalid"))

    def test_i18n_readiness_fallback_rules(self):
        self.assertTrue(self.i18n_readiness.is_effective_fallback("hello", "hello"))
        self.assertFalse(self.i18n_readiness.is_effective_fallback("{name}", "{name}"))
        self.assertFalse(self.i18n_readiness.is_effective_fallback("hello", "bonjour"))

    def test_update_pipeline_status_helpers(self):
        self.assertEqual(self.update_pipeline_status.normalize_run_id(" 123 "), "123")
        self.assertEqual(self.update_pipeline_status.normalize_run_id(""), "")

    def test_score_submission_normalize(self):
        self.assertEqual(self.score_submission.normalize("  Hello   World  "), "hello world")
        self.assertEqual(self.score_submission.normalize(""), "")

    def test_retirement_helpers(self):
        refs = self.retirement_candidates.parse_csv_refs("qwen3:8b=96, qwen2.5, qwen3:8b")
        self.assertEqual(refs, ["qwen3:8b", "qwen2.5"])
        self.assertTrue(self.retirement_candidates.matches_plan("qwen3:8b-q4_k_m", ["qwen3:8b"]))
        self.assertEqual(self.review_retirement.to_int("7", default=0), 7)
        self.assertEqual(self.review_retirement.to_int("bad", default=3), 3)

    def test_refresh_affiliate_parse_supported_routes(self):
        js_text = """
const AMAZON_RECOMMENDATIONS = {
  "rtx-3090-24gb": { label: "x" },
  "rtx-4090-24gb": { label: "y" }
};
function buildProviderTarget(provider, env) {
  if (provider === "runpod") { return {}; }
  if (provider === "vast") { return {}; }
  return null;
}
"""
        path = ROOT / "tmp-affiliate-lib.js"
        path.write_text(js_text, encoding="utf-8")
        try:
            providers, slugs = self.refresh_affiliate.parse_supported_routes(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(providers, {"runpod", "vast"})
        self.assertEqual(slugs, {"rtx-3090-24gb", "rtx-4090-24gb"})

    def test_refresh_affiliate_validate_link_paths(self):
        links = {
            "runpod": "/go/runpod",
            "amazon_3090": "/recommends/rtx-3090-24gb",
            "bad": "/go/unknown",
        }
        passed, failed = self.refresh_affiliate.validate_link_paths(
            links,
            providers={"runpod", "vast"},
            slugs={"rtx-3090-24gb"},
        )
        self.assertEqual(len(passed), 2)
        self.assertEqual(len(failed), 1)
        self.assertIn("unsupported /go provider", failed[0])


if __name__ == "__main__":
    unittest.main()
