import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('publish_daily_test',ROOT/'scripts/publish-content-queue.py')
publish=importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)
class DailyNoFillerTests(unittest.TestCase):
    def test_empty_review_queue_does_not_manufacture_a_daily_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);queue=root/'queue';(queue/'2026-09-20').mkdir(parents=True);blog=root/'blog';blog.mkdir()
            with patch.multiple(publish,QUEUE_ROOT=queue,BLOG_DIR=blog,LOG_FILE=root/'log.json',UPDATES_FILE=root/'updates.json'), patch.object(sys,'argv',['publish-content-queue.py','--queue-date','2026-09-20']), patch.dict(os.environ,{},clear=True), patch.object(publish,'build_daily_fallback_content') as fallback:
                publish.main()
                fallback.assert_not_called()
            self.assertEqual(list(blog.glob('*.md')),[])
            self.assertEqual(json.loads((root/'log.json').read_text())['last_run']['published_count'],0)
