"""Exercise validation failures without mounting images or probing the host."""

import ast
import atexit
import logging
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from method_loader import load_method


class ValidationTests(unittest.TestCase):
    def test_explicit_kernel_minor_zero_is_not_replaced_by_host_version(self):
        path = "opencore_legacy_patcher/sys_patch/patchsets/detect.py"
        tree = ast.parse((Path(__file__).resolve().parents[1] / path).read_text())
        namespace = {"constants": types.SimpleNamespace(Constants=object)}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("hardware."):
                namespace.update({alias.name: Mock() for alias in node.names})
        constructor = load_method(path, "HardwarePatchsetDetection", "__init__", namespace)
        constants = types.SimpleNamespace(detected_os=24, detected_os_minor=6, detected_os_build="24G", detected_os_version="15.7")
        for supplied, expected in [(0, 0), (None, 6), (3, 3)]:
            with self.subTest(minor=supplied):
                detector = types.SimpleNamespace(_detect=Mock())
                constructor(detector, constants, xnu_major=25, xnu_minor=supplied, validation=True)
                self.assertEqual(detector._xnu_minor, expected)
                self.assertEqual(detector._xnu_major, 25)
                detector._detect.assert_called_once()

    def test_detach_failure_is_accepted_only_if_volume_is_already_unmounted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            overlay = root / "Universal-Binaries_overlay"
            overlay.write_bytes(b"shadow")
            namespace = {"detach_disk_image": Mock(return_value=subprocess.CompletedProcess([], 1)), "subprocess_wrapper": types.SimpleNamespace(log=Mock()), "logging": logging}
            method = load_method("opencore_legacy_patcher/support/validation.py", "PatcherValidation", "_unmount_dmg", namespace)
            with patch.object(Path, "is_mount", side_effect=[True, False]):
                method(types.SimpleNamespace(constants=types.SimpleNamespace(payload_path=root)))
            self.assertFalse(overlay.exists())

    def test_root_validation_always_detaches_after_a_patch_file_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "Universal-Binaries.dmg"
            image.touch()
            os_names = ["big_sur", "monterey", "ventura", "sonoma", "sequoia", "tahoe"]
            namespace = {"Path": Path, "logging": logging, "atexit": atexit, "subprocess": types.SimpleNamespace(PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT, run=Mock(return_value=subprocess.CompletedProcess([], 0))), "os_data": types.SimpleNamespace(os_data=types.SimpleNamespace(**dict.fromkeys(os_names, 25)))}
            method = load_method("opencore_legacy_patcher/support/validation.py", "PatcherValidation", "_validate_sys_patch", namespace)
            failure = ValueError("missing patch file")
            worker = types.SimpleNamespace(constants=types.SimpleNamespace(payload_path=root, payload_local_binaries_root_path_dmg=image), _unmount_dmg=Mock(), _validate_root_patch_files=Mock(side_effect=failure))
            with patch.object(atexit, "register") as register, patch.object(atexit, "unregister") as unregister:
                with self.assertRaisesRegex(ValueError, "missing patch file"):
                    method(worker)
            self.assertEqual(worker._unmount_dmg.call_count, 2)
            register.assert_called_once_with(worker._unmount_dmg)
            unregister.assert_called_once_with(worker._unmount_dmg)
