import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "fetch-search-console-keywords.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module():
    spec = importlib.util.spec_from_file_location("fetch_search_console_keywords", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FetchSearchConsoleKeywordsTests(unittest.TestCase):
    def test_build_service_uses_adc_when_credentials_json_is_empty(self):
        mod = load_module()
        calls = []
        original_modules = {name: sys.modules.get(name) for name in [
            "google",
            "google.auth",
            "google.oauth2",
            "google.oauth2.service_account",
            "googleapiclient",
            "googleapiclient.discovery",
        ]}

        google_mod = types.ModuleType("google")
        auth_mod = types.ModuleType("google.auth")
        oauth2_mod = types.ModuleType("google.oauth2")
        service_account_mod = types.ModuleType("google.oauth2.service_account")
        googleapiclient_mod = types.ModuleType("googleapiclient")
        discovery_mod = types.ModuleType("googleapiclient.discovery")

        def fake_default(scopes):
            calls.append(("default", scopes))
            return "adc-creds", "project-id"

        def fake_build(api, version, credentials, cache_discovery):
            calls.append(("build", api, version, credentials, cache_discovery))
            return {"ok": True}

        auth_mod.default = fake_default
        discovery_mod.build = fake_build
        service_account_mod.Credentials = types.SimpleNamespace(from_service_account_info=lambda info, scopes: "json-creds")
        google_mod.auth = auth_mod
        oauth2_mod.service_account = service_account_mod
        googleapiclient_mod.discovery = discovery_mod

        sys.modules["google"] = google_mod
        sys.modules["google.auth"] = auth_mod
        sys.modules["google.oauth2"] = oauth2_mod
        sys.modules["google.oauth2.service_account"] = service_account_mod
        sys.modules["googleapiclient"] = googleapiclient_mod
        sys.modules["googleapiclient.discovery"] = discovery_mod
        try:
            self.assertEqual(mod.build_service(""), {"ok": True})
        finally:
            for name, module in original_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module

        self.assertEqual(calls[0], ("default", mod.SCOPES))
        self.assertEqual(calls[1], ("build", "searchconsole", "v1", "adc-creds", False))


if __name__ == "__main__":
    unittest.main()
