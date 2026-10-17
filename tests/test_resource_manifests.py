import logging
import types
import unittest
from unittest.mock import Mock

import requests

from method_loader import load_method


class ManifestTests(unittest.TestCase):
    def test_malformed_catalog_does_not_crash_or_poison_cache(self):
        cases = [
            ("kdk_handler", "KernelDebugKitObject", "_get_remote_kdks", "KDK_ASSET_LIST", "KDK_API_LINK"),
            ("metallib_handler", "MetalLibraryObject", "_get_remote_metallibs", "METALLIB_ASSET_LIST", "METALLIB_API_LINK"),
        ]
        for file_name, cls, method_name, cache, url in cases:
            for payload in (ValueError("invalid JSON"), {"error": "unavailable"}, [None], [{"build": "25A"}]):
                with self.subTest(catalog=file_name, payload=str(payload)):
                    response = Mock(status_code=200)
                    if isinstance(payload, Exception):
                        response.json.side_effect = payload
                    else:
                        response.json.return_value = payload
                    network = Mock()
                    network.NetworkUtilities.return_value.get.return_value = response
                    namespace = {cache: None, url: "https://example.test/catalog", "network_handler": network, "logging": logging, "requests": requests}
                    method = load_method(f"opencore_legacy_patcher/support/{file_name}.py", cls, method_name, namespace)
                    result = method(types.SimpleNamespace(constants=types.SimpleNamespace(patcher_version="3.0.0-rc.3")))
                    self.assertIsNone(result)
                    self.assertIsNone(namespace[cache])

    def test_valid_catalog_is_cached_unchanged(self):
        response = Mock(status_code=200)
        assets = [{"build": "25A354", "version": "26.0", "url": "https://example.test/kdk", "fileSize": 123}]
        response.json.return_value = assets
        network = Mock()
        network.NetworkUtilities.return_value.get.return_value = response
        namespace = {"KDK_ASSET_LIST": None, "KDK_API_LINK": "https://example.test/catalog", "network_handler": network, "logging": logging, "requests": requests}
        method = load_method("opencore_legacy_patcher/support/kdk_handler.py", "KernelDebugKitObject", "_get_remote_kdks", namespace)
        instance = types.SimpleNamespace(constants=types.SimpleNamespace(patcher_version="3.0.0-rc.3"))
        self.assertIs(method(instance), assets)
        self.assertIs(method(instance), assets)
        network.NetworkUtilities.return_value.get.assert_called_once()
