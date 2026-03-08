import importlib.util
import shutil
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "resolve-weekly-targets.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("resolve_weekly_targets", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ResolveWeeklyTargetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_parse_retry_delays(self):
        values = self.mod.parse_retry_delays("5, -1,abc, 0, 2.5")
        self.assertEqual(values, [5.0, 0.0, 2.5])

    def test_parse_targets_dedup_and_floor(self):
        values = self.mod.parse_targets("QWEN3=8, qwen3=16,deepseek-r1=abc, qwen2.5")
        self.assertEqual(values, [("qwen3", 16), ("deepseek-r1", 96), ("qwen2.5", 96)])

    def test_parse_params_from_tag(self):
        self.assertEqual(self.mod.parse_params_from_tag("mixtral:8x7b-instruct"), 56.0)
        self.assertEqual(self.mod.parse_params_from_tag("qwen2.5:14b"), 14.0)
        self.assertEqual(self.mod.parse_params_from_tag("deepseek:r1-560m"), 0.56)
        self.assertIsNone(self.mod.parse_params_from_tag("qwen3"))

    def test_recommend_num_predict(self):
        self.assertEqual(self.mod.recommend_num_predict(None), 96)
        self.assertEqual(self.mod.recommend_num_predict(14), 128)
        self.assertEqual(self.mod.recommend_num_predict(20), 96)
        self.assertEqual(self.mod.recommend_num_predict(70), 64)
        self.assertEqual(self.mod.recommend_num_predict(122), 48)

    def test_resolve_default_endpoint_prefers_lv(self):
        with patch.dict(
            "os.environ",
            {"LV_OLLAMA_ENDPOINT": "http://10.0.0.2:11434", "OLLAMA_HOST": "http://127.0.0.1:11434"},
            clear=False,
        ):
            self.assertEqual(self.mod.resolve_default_endpoint(), "http://10.0.0.2:11434")

    def test_load_retired_policy(self):
        base_tmp = ROOT / ".tmp" / "unit-tests"
        base_tmp.mkdir(parents=True, exist_ok=True)
        tmp_dir = base_tmp / f"resolve-weekly-targets-{uuid.uuid4().hex}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            path = tmp_dir / "retired.json"
            path.write_text(
                (
                    '{"retired_families":["Qwen3","qwen3"],'
                    '"retired_tags":["QWEN3:8B","qwen3:14b","qwen3:8b"]}'
                ),
                encoding="utf-8",
            )
            retired_families, retired_tags, loaded_path = self.mod.load_retired_policy(str(path))
            self.assertEqual(retired_families, {"qwen3"})
            self.assertEqual(retired_tags, {"qwen3:8b", "qwen3:14b"})
            self.assertEqual(loaded_path, str(path))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
