"""Test copy failures and signature restoration using temporary files only."""

import enum
import importlib.util
import logging
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from method_loader import load_function, load_method


def load_wrapper():
    spec = importlib.util.spec_from_file_location("root_copy_wrapper", Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/support/subprocess_wrapper.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RootFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.payload = self.root / "payload"
        self.payload.mkdir()
        self.mount = self.root / "mount"
        self.signature = self.mount / "System/Library/Extensions/IOHIDFamily.kext/Contents/PlugIns/IOHIDEventDriver.kext/Contents/_CodeSignature"
        self.signature.mkdir(parents=True)
        (self.signature / "CodeResources").write_text("KDK signature")
        self.backup = self.payload / "IOHIDEventDriver_CodeSignature.bak"
        self.wrapper = load_wrapper()
        # Execute the repository's real argument builder, disabling only macOS filesystem probing.
        self.copy = load_function("opencore_legacy_patcher/volume/copy.py", "generate_copy_arguments", {"Path": Path, "can_copy_on_write": lambda source, destination: False})
        self.namespace = {"Path": Path, "logging": logging, "subprocess": subprocess, "subprocess_wrapper": self.wrapper, "generate_copy_arguments": self.copy}
        self.worker = types.SimpleNamespace(mount_location=str(self.mount), constants=types.SimpleNamespace(payload_path=self.payload))

    def method(self, name):
        return load_method("opencore_legacy_patcher/sys_patch/utilities/kdk_merge.py", "KernelDebugKitMerge", name, self.namespace)

    def make_backup(self):
        self.backup.mkdir()
        (self.backup / "CodeResources").write_text("original signature")

    def test_signature_is_restored_into_existing_directory_without_nesting(self):
        self.make_backup()
        with patch.object(self.wrapper, "run_as_root", side_effect=subprocess.run):
            self.method("_restore_hid_cs")(self.worker)
        self.assertEqual((self.signature / "CodeResources").read_text(), "original signature")
        self.assertFalse((self.signature / self.backup.name).exists())
        self.assertFalse(self.backup.exists())

    def test_restore_creates_missing_signature_directory(self):
        self.make_backup()
        (self.signature / "CodeResources").unlink()
        self.signature.rmdir()
        with patch.object(self.wrapper, "run_as_root", side_effect=subprocess.run):
            self.method("_restore_hid_cs")(self.worker)
        self.assertEqual((self.signature / "CodeResources").read_text(), "original signature")

    def test_failed_restore_keeps_backup_and_stops_before_deleting_it(self):
        self.make_backup()
        failed = subprocess.CompletedProcess([], 1, b"copy failed", b"")
        with patch.object(self.wrapper, "run_as_root", return_value=failed) as run:
            with self.assertRaises(Exception):
                self.method("_restore_hid_cs")(self.worker)
        self.assertEqual((self.backup / "CodeResources").read_text(), "original signature")
        self.assertEqual(run.call_count, 1)
        self.assertEqual((self.signature / "CodeResources").read_text(), "KDK signature")

    def test_failed_signature_backup_is_not_silently_accepted(self):
        with patch.object(self.wrapper, "run_as_root", return_value=subprocess.CompletedProcess([], 1, b"copy failed", b"")):
            with self.assertRaises(Exception):
                self.method("_backup_hid_cs")(self.worker)

    def test_pending_signature_backup_is_not_overwritten_or_nested_on_retry(self):
        self.make_backup()
        with patch.object(self.wrapper, "run_as_root", side_effect=subprocess.run) as run:
            with self.assertRaises(FileExistsError):
                self.method("_backup_hid_cs")(self.worker)
        run.assert_not_called()
        self.assertEqual((self.backup / "CodeResources").read_text(), "original signature")
        self.assertFalse((self.backup / "_CodeSignature").exists())

    def test_failed_kdk_merge_is_not_masked_by_preexisting_libkern(self):
        libkern = self.mount / "System/Library/Extensions/System.kext/PlugIns/Libkern.kext/Libkern"
        libkern.parent.mkdir(parents=True)
        libkern.write_bytes(b"already present")
        failed = subprocess.CompletedProcess([], 23, b"rsync partial transfer", b"")
        with patch.object(self.wrapper, "run_as_root", return_value=failed):
            with self.assertRaises(Exception):
                self.method("_merge_kdk")(self.worker, str(self.root / "KDK"))

    def test_failed_patch_merge_stops_before_fixing_permissions(self):
        patch_type = enum.Enum("PatchType", ["MERGE_SYSTEM_VOLUME", "MERGE_DATA_VOLUME"])
        fix_permissions = Mock()
        namespace = {**self.namespace, "PatchType": patch_type, "fix_permissions": fix_permissions}
        method = load_function("opencore_legacy_patcher/sys_patch/utilities/files.py", "install_new_file", namespace)
        with patch.object(self.wrapper, "run_as_root", return_value=subprocess.CompletedProcess([], 23, b"partial copy", b"")):
            with self.assertRaises(Exception):
                method(str(self.payload), str(self.mount), "Example.framework", patch_type.MERGE_SYSTEM_VOLUME)
        fix_permissions.assert_not_called()

    def test_successful_patch_merge_preserves_command_and_permission_fix(self):
        patch_type = enum.Enum("PatchType", ["MERGE_SYSTEM_VOLUME", "MERGE_DATA_VOLUME"])
        fix_permissions = Mock()
        namespace = {**self.namespace, "PatchType": patch_type, "fix_permissions": fix_permissions}
        method = load_function("opencore_legacy_patcher/sys_patch/utilities/files.py", "install_new_file", namespace)
        with patch.object(self.wrapper, "run_as_root", return_value=subprocess.CompletedProcess([], 0, b"", b"")) as run:
            method(str(self.payload), str(self.mount), "Example.framework", patch_type.MERGE_SYSTEM_VOLUME)
        self.assertEqual(run.call_args.args[0], ["/usr/bin/rsync", "-r", "-i", "-a", f"{self.payload}/Example.framework", f"{self.mount}/"])
        fix_permissions.assert_called_once_with(f"{self.mount}/Example.framework")
