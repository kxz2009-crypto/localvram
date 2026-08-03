import importlib.util
import shutil
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "check-cn-blog-sync.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("check_cn_blog_sync", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CnBlogSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def setUp(self):
        base_tmp = ROOT / ".tmp" / "unit-tests"
        base_tmp.mkdir(parents=True, exist_ok=True)
        self.tmp_dir = base_tmp / f"cn-blog-sync-{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.original_cn_dir = self.mod.CN_BLOG_DIR
        self.mod.CN_BLOG_DIR = self.tmp_dir

    def tearDown(self):
        self.mod.CN_BLOG_DIR = self.original_cn_dir
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def write_zh(self, slug, body):
        path = self.tmp_dir / f"{slug}.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_rejects_stub_by_default(self):
        self.write_zh("stub-post", "---\ntitle: Stub\n---\nstatus: zh-stub (pending full translation)\n")

        issue = self.mod.validate_cn_translation("stub-post", min_cjk_chars=12)

        self.assertIn("zh translation is still a stub placeholder", issue)

    def test_allows_stub_when_requested(self):
        self.write_zh("stub-post", "---\ntitle: Stub\n---\nstatus: zh-stub (pending full translation)\n")

        issue = self.mod.validate_cn_translation("stub-post", min_cjk_chars=12, allow_stub=True)

        self.assertIsNone(issue)


if __name__ == "__main__":
    unittest.main()
