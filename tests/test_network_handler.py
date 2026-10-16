"""Exercise the real downloader with local streams and simulated HTTP failures."""

import hashlib
import importlib.util
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


def load_network():
    packages = {name: types.ModuleType(name) for name in ("network_test", "network_test.support", "network_test.support.utilities")}
    packages["network_test"].__path__ = []
    packages["network_test.support"].__path__ = []
    utilities = packages["network_test.support.utilities"]
    utilities.get_free_space = Mock(return_value=10**12)
    utilities.human_fmt = str
    utilities.disable_sleep_while_running = Mock()
    utilities.enable_sleep_after_running = Mock()
    spec = importlib.util.spec_from_file_location("network_test.support.network_handler", Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/support/network_handler.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, packages):
        spec.loader.exec_module(module)
    return module


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.network = load_network()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.destination = Path(self.tmp.name) / "payload.pkg"
        self.destination.write_bytes(b"previous valid package")
        self.addCleanup(patch.stopall)
        patch.object(self.network.NetworkUtilities, "verify_network_connection", return_value=True).start()
        patch.object(self.network.SESSION, "head", return_value=Mock(headers={})).start()

    def response(self, status=200, body=b"replacement", length=None, encoded=False):
        result = requests.Response()
        result.status_code = status
        result.url = "https://example.test/payload.pkg"
        result.raw = io.BytesIO(body)
        result.close = Mock(wraps=result.close)
        result.headers["Content-Length"] = str(len(body) if length is None else length)
        if encoded:
            result.headers["Content-Encoding"] = "gzip"
        return result

    def run_download(self, response):
        with patch.object(self.network.SESSION, "get", return_value=response):
            download = self.network.DownloadObject("https://example.test/payload.pkg", self.destination)
            download.download(spawn_thread=False)
        return download

    def assert_failed_and_preserved(self, download):
        self.assertFalse(download.download_complete)
        self.assertTrue(download.error)
        self.assertEqual(download.status, self.network.DownloadStatus.ERROR)
        self.assertEqual(self.destination.read_bytes(), b"previous valid package")
        self.assertEqual(list(self.destination.parent.glob("*.part")), [])
        self.network.utilities.enable_sleep_after_running.assert_called_once()

    def test_http_error_does_not_replace_existing_package(self):
        for status in (404, 403, 500):
            with self.subTest(status=status):
                self.network.utilities.enable_sleep_after_running.reset_mock()
                self.assert_failed_and_preserved(self.run_download(self.response(status=status, body=b"error page")))

    def test_short_body_is_not_reported_as_complete(self):
        self.assert_failed_and_preserved(self.run_download(self.response(body=b"abc", length=100)))

    def test_connection_failure_uses_error_response_and_preserves_package(self):
        with patch.object(self.network.SESSION, "get", side_effect=requests.ConnectionError("offline")):
            download = self.network.DownloadObject("https://example.test/payload.pkg", self.destination)
            download.download(spawn_thread=False)
        self.assert_failed_and_preserved(download)

    def test_interrupted_body_is_cleaned_up(self):
        response = self.response(length=100)
        def chunks(*args):
            yield b"partially downloaded"
            raise requests.ConnectionError("stream interrupted")
        response.iter_content = chunks
        self.assert_failed_and_preserved(self.run_download(response))

    def test_success_replaces_destination_and_hashes_only_received_bytes(self):
        response = self.response()
        with patch.object(self.network.SESSION, "get", return_value=response):
            download = self.network.DownloadObject("https://example.test/payload.pkg", self.destination)
            self.assertEqual(download.download_simple(verify_checksum=True), hashlib.sha256(b"replacement").hexdigest())
        response.close.assert_called_once()
        self.assertEqual(self.destination.read_bytes(), b"replacement")
        self.assertEqual(download.status, self.network.DownloadStatus.COMPLETE)

    def test_completed_thread_can_be_retried_with_reset_counters_and_checksum(self):
        with patch.object(self.network.SESSION, "get", side_effect=[self.response(body=b"first"), self.response(body=b"second")]):
            download = self.network.DownloadObject("https://example.test/payload.pkg", self.destination, hashlib.sha256())
            for body in (b"first", b"second"):
                download.download()
                download.active_thread.join(timeout=2)
                self.assertFalse(download.active_thread.is_alive())
                self.assertTrue(download.download_complete)
                self.assertEqual(download.downloaded_file_size, len(body))
                self.assertEqual(download.checksum, hashlib.sha256(body).hexdigest())
        self.assertEqual(self.destination.read_bytes(), b"second")

    def test_cancellation_after_last_chunk_does_not_commit_file(self):
        response = self.response()
        download = self.network.DownloadObject("https://example.test/payload.pkg", self.destination)
        def chunks(*args):
            yield b"replacement"
            download.should_stop = True
        response.iter_content = chunks
        with patch.object(self.network.SESSION, "get", return_value=response):
            download.download(spawn_thread=False)
        self.assert_failed_and_preserved(download)

    def test_space_check_also_applies_when_destination_already_exists(self):
        self.network.utilities.get_free_space.return_value = 0
        self.assert_failed_and_preserved(self.run_download(self.response()))

    def test_content_encoding_does_not_compare_compressed_size_with_decoded_bytes(self):
        download = self.run_download(self.response(body=b"decoded content", length=3, encoded=True))
        self.assertTrue(download.download_complete)
        self.assertEqual(self.destination.read_bytes(), b"decoded content")

    def test_speed_is_defined_at_start_of_download(self):
        download = self.network.DownloadObject("https://example.test/payload.pkg", self.destination)
        with patch.object(self.network.time, "time", return_value=download.start_time):
            self.assertEqual(download.get_speed(), 0)

    def test_failed_network_wrapper_response_has_valid_http_status(self):
        with patch.object(self.network.SESSION, "get", side_effect=requests.ConnectionError("offline")):
            response = self.network.NetworkUtilities().get("https://example.test")
        with self.assertRaises(requests.HTTPError):
            response.raise_for_status()
        response.close()


if __name__ == "__main__":
    unittest.main()
