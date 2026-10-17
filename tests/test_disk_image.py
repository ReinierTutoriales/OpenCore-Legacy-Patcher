import errno
import importlib.util
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from method_loader import load_method

spec = importlib.util.spec_from_file_location("disk_image", Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/support/disk_image.py")
disk_image = importlib.util.module_from_spec(spec)
spec.loader.exec_module(disk_image)


class DetachTests(unittest.TestCase):
    def test_busy_is_retried_and_success_returned(self):
        results = [subprocess.CompletedProcess([], errno.EBUSY), subprocess.CompletedProcess([], 0)]
        with patch.object(disk_image.subprocess, "run", side_effect=results) as run, patch.object(disk_image.time, "sleep") as sleep:
            self.assertEqual(disk_image.detach_disk_image("/Volumes/test").returncode, 0)
        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_permanent_failure_is_not_hidden_or_retried(self):
        result = subprocess.CompletedProcess([], 1)
        with patch.object(disk_image.subprocess, "run", return_value=result) as run, patch.object(disk_image.time, "sleep") as sleep:
            self.assertIs(disk_image.detach_disk_image("/Volumes/test"), result)
        run.assert_called_once()
        sleep.assert_not_called()

    def test_busy_retry_count_is_bounded(self):
        with patch.object(disk_image.subprocess, "run", return_value=subprocess.CompletedProcess([], errno.EBUSY)) as run, patch.object(disk_image.time, "sleep"):
            self.assertEqual(disk_image.detach_disk_image("/Volumes/test").returncode, errno.EBUSY)
        self.assertEqual(run.call_count, 3)

    def test_failed_detach_preserves_shadow_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            overlay = root / "Universal-Binaries_overlay"
            overlay.write_bytes(b"active shadow")
            namespace = {"detach_disk_image": Mock(return_value=subprocess.CompletedProcess([], errno.EBUSY)), "subprocess_wrapper": types.SimpleNamespace(log=Mock()), "logging": Mock()}
            method = load_method("opencore_legacy_patcher/support/validation.py", "PatcherValidation", "_unmount_dmg", namespace)
            instance = types.SimpleNamespace(constants=types.SimpleNamespace(payload_path=root))
            with patch.object(Path, "is_mount", return_value=True), self.assertRaises(Exception):
                method(instance)
            self.assertEqual(overlay.read_bytes(), b"active shadow")

    def test_empty_mount_directory_is_not_detached(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Universal-Binaries").mkdir()
            namespace = {"detach_disk_image": Mock(), "logging": Mock()}
            method = load_method("opencore_legacy_patcher/support/validation.py", "PatcherValidation", "_unmount_dmg", namespace)
            method(types.SimpleNamespace(constants=types.SimpleNamespace(payload_path=root)))
            namespace["detach_disk_image"].assert_not_called()
