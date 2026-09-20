import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('weekly_identity',ROOT/'scripts/weekly-benchmark.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class BenchmarkIdentityTests(unittest.TestCase):
    def test_reads_actual_digest_and_quantization_not_requested_label(self):
        payload={'models':[{'name':'model:latest','digest':'a'*64,'details':{'quantization_level':'Q4_K_M'}}]}
        with patch.object(module,'api_request',return_value=payload):
            self.assertEqual(module.fetch_model_identity('http://localhost','model'),{'model_digest':'sha256:'+'a'*64,'quantization':'Q4_K_M'})
            self.assertEqual(module.fetch_model_identity('http://localhost','different'),{})
    def test_metadata_errors_and_changed_files_cannot_gain_identity(self):
        with patch.object(module,'api_request',side_effect=RuntimeError('offline')):
            self.assertEqual(module.fetch_model_identity('http://localhost','model'),{})
        a={'model_digest':'a','quantization':'Q4_K_M'}
        self.assertEqual(module.stable_model_identity(a,a),a)
        self.assertEqual(module.stable_model_identity(a,{**a,'model_digest':'b'}),{})
        self.assertEqual(module.stable_model_identity({},{}),{})

    def test_identity_changes_publish_even_with_unchanged_throughput(self):
        old={'status':'ok','tokens_per_second':42}
        identified={**old,'model_digest':'sha256:'+'a'*64,'quantization':'Q4_K_M'}
        self.assertTrue(module.has_significant_change(old,identified,10))
        self.assertTrue(module.has_significant_change(identified,old,10))
        self.assertFalse(module.has_significant_change(identified,identified,10))
