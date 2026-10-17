"""Exercise update responses without loading AppKit or probing the host Mac."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


class UpdateTests(unittest.TestCase):
    def setUp(self):
        modules = {name: types.ModuleType(name) for name in ["update_test", "update_test.support", "update_test.constants", "update_test.support.network_handler"]}
        modules["update_test"].__path__ = []
        modules["update_test.support"].__path__ = []
        modules["update_test.constants"].Constants = types.SimpleNamespace
        self.network = modules["update_test.support.network_handler"]
        self.network.requests = requests
        self.response = Mock()
        self.network.NetworkUtilities = Mock(return_value=Mock(get=Mock(return_value=self.response)))
        spec = importlib.util.spec_from_file_location("update_test.support.updates", Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/support/updates.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, modules):
            spec.loader.exec_module(module)
        self.constants = types.SimpleNamespace(patcher_version="3.0.0-rc.3", special_build=False, commit_info=["refs/tags/3.0.0-rc.3"], repo_link="https://github.com/ReinierTutoriales/OpenCore-Legacy-Patcher")
        self.checker = module.CheckBinaryUpdates(self.constants)

    def release(self, tag, prerelease=False):
        return {"tag_name": tag, "prerelease": prerelease, "draft": False, "assets": [{"name": "OpenCore-Patcher.pkg", "browser_download_url": f"{self.constants.repo_link}/releases/download/{tag}/OpenCore-Patcher.pkg"}]}

    def test_rc_channel_uses_fork_and_newest_compatible_package(self):
        self.response.json.return_value = [self.release("3.0.0-rc.2", True), self.release("3.0.0-rc.4", True), self.release("2.5.1")]
        result = self.checker.check_binary_updates()
        self.assertEqual(str(result["Version"]), "3.0.0rc4")
        self.assertIn("ReinierTutoriales", result["Link"])
        self.network.NetworkUtilities.return_value.get.assert_called_once_with("https://api.github.com/repos/ReinierTutoriales/OpenCore-Legacy-Patcher/releases", timeout=(5, 15))

    def test_stable_channel_does_not_accept_prerelease_even_if_mislabeled(self):
        self.checker.binary_version = self.checker.binary_version.__class__("2.5.0")
        self.response.json.return_value = [self.release("3.0.0-rc.4"), self.release("2.5.1")]
        self.assertEqual(str(self.checker.check_binary_updates()["Version"]), "2.5.1")

    def test_draft_missing_asset_and_malformed_entries_are_ignored(self):
        draft = self.release("4.0.0"); draft["draft"] = True
        missing = self.release("5.0.0"); missing["assets"] = [None, "broken", {"name": "OpenCore-Patcher.pkg"}]
        self.response.json.return_value = [None, draft, missing, self.release("invalid"), self.release("3.0.0-rc.4", True)]
        self.assertEqual(str(self.checker.check_binary_updates()["Version"]), "3.0.0rc4")

    def test_foreign_download_is_rejected(self):
        foreign = self.release("4.0.0")
        foreign["assets"][0]["browser_download_url"] = "https://example.org/pkg"
        self.response.json.return_value = [foreign]
        self.assertIsNone(self.checker.check_binary_updates())

    def test_http_and_json_errors_do_not_escape(self):
        for error in [requests.exceptions.Timeout("timeout"), requests.exceptions.HTTPError("rate limited"), ValueError("invalid JSON")]:
            with self.subTest(error=type(error).__name__):
                self.response.json.side_effect = error
                self.assertIsNone(self.checker.check_binary_updates())

    def test_equal_or_older_versions_do_not_update(self):
        self.response.json.return_value = [self.release("3.0.0-rc.3", True), self.release("2.5.1")]
        self.assertIsNone(self.checker.check_binary_updates())

    def test_network_wrapper_failure_is_handled_without_type_error(self):
        from test_network_handler import load_network
        network = load_network()
        with patch.object(network.SESSION, "get", side_effect=requests.ConnectionError("offline")):
            response = network.NetworkUtilities().get("https://api.github.com")
        self.network.NetworkUtilities.return_value.get.return_value = response
        self.assertIsNone(self.checker.check_binary_updates())


if __name__ == "__main__":
    unittest.main()
