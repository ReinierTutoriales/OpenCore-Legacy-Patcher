import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("efi_transaction", Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/support/efi_transaction.py")
efi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(efi)


class EFITransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source, self.mount = self.base / "build", self.base / "esp"
        self.mount.mkdir()
        for root, files in [(self.source, {"EFI/OC/OpenCore.efi": "new", "EFI/OC/config.plist": "config", "System/Library/CoreServices/boot.efi": "boot"}), (self.mount, {"EFI/OC/OpenCore.efi": "old", "System/old": "old-system", "EFI/BOOT/BOOTx64.efi": "old-bootstrap", "EFI/Microsoft/Boot/bootmgfw.efi": "windows"})]:
            for name, data in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(data)

    def test_install_preserves_backup_and_other_loaders(self):
        backup = efi.install_efi(self.source, self.mount)
        self.assertEqual((self.mount / "EFI/OC/OpenCore.efi").read_text(), "new")
        self.assertEqual((backup / "EFI/OC/OpenCore.efi").read_text(), "old")
        self.assertEqual((self.mount / "EFI/Microsoft/Boot/bootmgfw.efi").read_text(), "windows")
        self.assertEqual((self.mount / "EFI/BOOT/BOOTx64.efi").read_text(), "old-bootstrap")
        self.assertEqual(json.loads((backup / "transaction.json").read_text())["state"], "complete")
        self.assertFalse((self.mount / ".OCLP-install.lock").exists())

    def test_boot_conversion_is_backed_up(self):
        backup = efi.install_efi(self.source, self.mount, True)
        self.assertEqual((self.mount / "EFI/BOOT/BOOTx64.efi").read_text(), "boot")
        self.assertEqual((backup / "EFI/BOOT/BOOTx64.efi").read_text(), "old-bootstrap")
        self.assertFalse((self.mount / "System").exists())

    def test_copy_failure_does_not_touch_active_efi(self):
        with patch.object(efi.shutil, "copytree", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                efi.install_efi(self.source, self.mount)
        self.assertEqual((self.mount / "EFI/OC/OpenCore.efi").read_text(), "old")
        self.assertFalse((self.mount / ".OCLP-install.lock").exists())

    def test_commit_failure_restores_original_files(self):
        rename = Path.rename
        def fail_once(path, target):
            if ".OCLP-Staging-" in str(path) and str(path).endswith("/System"):
                raise OSError("simulated write failure")
            return rename(path, target)
        with patch.object(Path, "rename", fail_once):
            with self.assertRaises(OSError):
                efi.install_efi(self.source, self.mount)
        self.assertEqual((self.mount / "EFI/OC/OpenCore.efi").read_text(), "old")
        self.assertEqual((self.mount / "System/old").read_text(), "old-system")
        self.assertFalse((self.mount / ".OCLP-install.lock").exists())

    def test_corrupt_staged_copy_is_rejected(self):
        copy = efi.shutil.copytree
        def corrupt(source, destination, **kwargs):
            result = copy(source, destination, **kwargs)
            if (destination / "OpenCore.efi").exists():
                (destination / "OpenCore.efi").write_text("corrupted")
            return result
        with patch.object(efi.shutil, "copytree", corrupt):
            with self.assertRaises(OSError):
                efi.install_efi(self.source, self.mount)
        self.assertEqual((self.mount / "EFI/OC/OpenCore.efi").read_text(), "old")

    def test_existing_lock_prevents_concurrent_install(self):
        lock = self.mount / ".OCLP-install.lock"
        lock.mkdir()
        with self.assertRaises(FileExistsError):
            efi.install_efi(self.source, self.mount)
        self.assertTrue(lock.exists())

    def test_symlink_destination_is_rejected(self):
        external = self.base / "external"
        external.mkdir()
        (self.mount / "EFI/OC").rename(external / "OC")
        (self.mount / "EFI/OC").symlink_to(external / "OC", target_is_directory=True)
        with self.assertRaises(ValueError):
            efi.install_efi(self.source, self.mount)
        self.assertEqual((external / "OC/OpenCore.efi").read_text(), "old")

    def test_insufficient_space_and_incomplete_build_leave_efi_untouched(self):
        usage = efi.shutil.disk_usage(self.mount)._replace(free=0)
        with patch.object(efi.shutil, "disk_usage", return_value=usage):
            with self.assertRaises(OSError):
                efi.install_efi(self.source, self.mount)
        (self.source / "EFI/OC/OpenCore.efi").unlink()
        with self.assertRaises(ValueError):
            efi.install_efi(self.source, self.mount)
        self.assertEqual((self.mount / "EFI/OC/OpenCore.efi").read_text(), "old")


if __name__ == "__main__":
    unittest.main()
