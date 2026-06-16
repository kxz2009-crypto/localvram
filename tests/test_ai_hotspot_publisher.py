import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "ai-hotspot-publisher.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("ai_hotspot_publisher", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AiHotspotPublisherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_markdown_to_wechat_html_escapes_raw_html(self):
        html = self.mod.markdown_to_wechat_html(
            "## Safe title\n\n<script>alert('x')</script>\n\n`<b>code</b>`"
        )

        self.assertIn("&lt;script&gt;alert('x')&lt;/script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;b&gt;code&lt;/b&gt;", html)

    def test_markdown_to_wechat_html_strips_markdown_links(self):
        html = self.mod.markdown_to_wechat_html("Read [source](https://example.com) now.")

        self.assertIn("Read source now.", html)
        self.assertNotIn("https://example.com", html)


if __name__ == "__main__":
    unittest.main()
