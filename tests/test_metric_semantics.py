import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class MetricSemanticsTests(unittest.TestCase):
    def test_funnel_keeps_channels_separate_and_dates_bounded(self):
        now = dt.datetime.now(dt.timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            sc = {'window': {'start_date': '2026-08-23', 'end_date': '2026-09-19', 'days': 28}, 'items': [
                {'clicks': 1, 'landing': '/de/models/example/'},
                {'clicks': 2, 'landing': '/tools/vram-calculator/'},
            ]}
            def event(ts, referer=''):
                return {'ts': ts, 'provider': 'runpod', 'route': '/go/runpod', 'referer': referer}
            events = [event((now-dt.timedelta(hours=1)).isoformat(), 'https://localvram.com/en/tools/vram-calculator/'),
                      event((now-dt.timedelta(hours=2)).isoformat(), 'https://external.example/en/models/example/'),
                      event('bad'),event((now+dt.timedelta(days=1)).isoformat()),event((now-dt.timedelta(days=40)).isoformat())]
            (path/'sc.json').write_text(json.dumps(sc))
            (path/'events.json').write_text(json.dumps({'events':events}))
            subprocess.run([sys.executable,str(ROOT/'scripts/build-conversion-funnel.py'),'--search-console-file',str(path/'sc.json'),'--affiliate-events-file',str(path/'events.json'),'--output-file',str(path/'out.json')], check=True,capture_output=True)
            data = json.loads((path/'out.json').read_text())
            self.assertEqual(data['funnel']['decision_page_clicks'],3)
            self.assertEqual(data['funnel']['affiliate_redirect_clicks'],2)
            self.assertIsNone(data['funnel']['search_to_affiliate_pct'])
            self.assertIsNone(data['funnel']['search_to_cloud_pct'])
            self.assertEqual(data['funnel']['cloud_share_of_redirects_pct'],100)
            self.assertEqual(data['sources']['search_console_window'],sc['window'])
            self.assertEqual(data['data_quality']['unattributed_redirects'],1)
            self.assertEqual(data['data_quality']['excluded_invalid_or_out_of_window_events'],3)

    def test_import_does_not_create_current_activity_for_unknown_or_future_dates(self):
        module = load('import-affiliate-events')
        now = dt.datetime.now(dt.timezone.utc)
        for ts in ['', 'bad', (now+dt.timedelta(days=1)).isoformat()]:
            self.assertIsNone(module.sanitize_event({'ts':ts,'route':'/go/runpod'},now))
        self.assertIsNotNone(module.sanitize_event({'ts':(now-dt.timedelta(days=1)).isoformat(),'route':'/go/runpod'},now))

    def test_legacy_kpi_migration_preserves_history_without_calling_it_index_coverage(self):
        module = load('refresh-locale-kpi')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'kpi.csv'
            path.write_text('date,locale,indexed_urls,index_rate_pct\n2026-09-01,de,3,1.5\n')
            rows = module.load_rows(path)
            self.assertEqual(rows[0]['visible_landing_urls'],'3')
            self.assertEqual(rows[0]['search_visibility_pct'],'1.5')
            module.save_rows(path,rows)
            self.assertNotIn('indexed_urls',path.read_text())
            self.assertEqual(module.load_rows(path)[0]['visible_landing_urls'],'3')

    def test_search_visibility_counts_distinct_landings_not_query_rows(self):
        module = load('refresh-locale-kpi')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sc.json'
            path.write_text(json.dumps({'items':[
                {'locale':'de','landing':'/de/models/a/','impressions':3,'clicks':0,'position':10},
                {'locale':'de','landing':'/de/models/a/','impressions':2,'clicks':0,'position':10},
                {'locale':'de','landing':'/de/models/b/','impressions':0,'clicks':0,'position':0},
            ]}))
            stats=module.parse_search_console(path,{'de'})
            self.assertEqual(stats['de']['visible_landing_urls'],1)
            self.assertEqual(stats['de']['impressions'],5)
