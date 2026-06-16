import importlib.util
import json
import shutil
import sys
import unittest
import uuid
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "import-gsc-performance-export.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("import_gsc_performance_export", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GscPerformanceExportImportTests(unittest.TestCase):
    def setUp(self):
        base_tmp = ROOT / ".tmp" / "unit-tests"
        base_tmp.mkdir(parents=True, exist_ok=True)
        self.tmp_dir = base_tmp / f"gsc-import-{uuid.uuid4().hex}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def write_zip(self):
        zip_path = self.tmp_dir / "gsc.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr(
                "查询数.csv",
                "\ufeff热门查询,点击次数,展示,点击率,排名\n"
                "best coding model for 24gb vram,1,2,50%,6.5\n"
                "local llm updates 2026,0,27,0%,5.81\n",
            )
            archive.writestr(
                "网页.csv",
                "\ufeff排名靠前的网页,点击次数,展示,点击率,排名\n"
                "https://localvram.com/en/blog/best-24gb-vram-models-2026/,2,1410,0.14%,8.83\n"
                "https://localvram.com/en/,2,57,3.51%,9.44\n",
            )
            archive.writestr("过滤器.csv", "\ufeff搜索类型,网页\n日期,过去 3 个月\n")
        return zip_path

    def test_imports_ui_export_without_inventing_query_page_pairs(self):
        mod = load_module()
        output = self.tmp_dir / "search-console-keywords.json"

        payload = mod.import_gsc_export(
            zip_path=self.write_zip(),
            output_path=output,
            imported_at="2026-04-27T16:00:00Z",
        )

        self.assertEqual(payload["source"], "google-search-console-ui-export")
        self.assertEqual(payload["updated_at"], "2026-04-27T16:00:00Z")
        self.assertEqual(payload["date_range_label"], "过去 3 个月")
        self.assertEqual(len(payload["query_items"]), 2)
        self.assertEqual(len(payload["page_items"]), 2)
        self.assertEqual(payload["items"], payload["page_items"])
        self.assertEqual(payload["query_items"][0]["query"], "local llm updates 2026")
        self.assertEqual(payload["query_items"][0]["ctr"], 0.0)
        first_page = payload["page_items"][0]
        self.assertEqual(first_page["landing"], "/en/blog/best-24gb-vram-models-2026/")
        self.assertEqual(first_page["locale"], "en")
        self.assertEqual(first_page["keyword"], "best 24gb vram models 2026")
        self.assertEqual(first_page["source_row_type"], "page")
        self.assertEqual(first_page["ctr"], 0.0014)
        self.assertTrue(output.exists())
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)

    def test_derives_section_keyword_for_locale_section_indexes(self):
        mod = load_module()

        self.assertEqual(mod.keyword_from_landing("/en/models/"), "models")
        self.assertEqual(mod.keyword_from_landing("/en/blog/"), "blog")
        self.assertEqual(mod.keyword_from_landing("/en/"), "home")


if __name__ == "__main__":
    unittest.main()
