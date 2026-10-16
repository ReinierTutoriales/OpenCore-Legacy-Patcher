import importlib.util
import plistlib
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("global_settings", Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/support/global_settings.py")
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "settings.plist"
        self.original = {"GUI:showpicker": True, "retained": "previous"}
        self.path.write_bytes(plistlib.dumps(self.original))
        self.store = settings.GlobalEnviromentSettings.__new__(settings.GlobalEnviromentSettings)
        self.store.global_settings_plist = str(self.path)

    def assert_original_preserved(self):
        self.assertEqual(plistlib.loads(self.path.read_bytes()), self.original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_invalid_value_never_truncates_existing_settings(self):
        for value in (None, object(), 2**128):
            with self.subTest(value=type(value).__name__):
                self.store.write_property("invalid", value)
                self.assert_original_preserved()

    def test_failed_replace_preserves_existing_settings_and_cleans_temporary_file(self):
        with patch.object(Path, "replace", side_effect=OSError("disk error")):
            self.store.write_property("new", "value")
        self.assert_original_preserved()

    def test_failed_flush_preserves_existing_settings(self):
        with patch.object(settings.os, "fsync", side_effect=OSError("disk full")):
            self.store.write_property("new", "value")
        self.assert_original_preserved()

    def test_successful_save_preserves_other_keys_and_permissions(self):
        self.path.chmod(0o640)
        before = self.path.stat()
        self.store.write_property("new", "value")
        self.assertEqual(self.store.read_property("new"), "value")
        self.assertEqual(self.store.read_property("retained"), "previous")
        after = self.path.stat()
        self.assertEqual(stat.S_IMODE(after.st_mode), 0o640)
        self.assertEqual((after.st_uid, after.st_gid), (before.st_uid, before.st_gid))

    def test_failed_delete_preserves_all_keys(self):
        with patch.object(Path, "replace", side_effect=PermissionError("read only")):
            self.store.delete_property("retained")
        self.assert_original_preserved()

    def test_successful_delete_preserves_remaining_keys(self):
        self.store.delete_property("retained")
        self.assertEqual(plistlib.loads(self.path.read_bytes()), {"GUI:showpicker": True})

    def test_legacy_preferences_are_not_deleted_when_migration_cannot_save(self):
        legacy = self.path.parent / "legacy.plist"
        legacy.write_bytes(plistlib.dumps({"legacy": "keep"}))
        with patch.object(Path, "expanduser", return_value=legacy), patch.object(Path, "replace", side_effect=OSError("cannot save")):
            self.store._convert_defaults_to_global_settings()
        self.assertTrue(legacy.exists())
        self.assert_original_preserved()

    def test_concurrent_initial_creation_never_overwrites_existing_settings(self):
        with patch.object(Path, "exists", return_value=False):
            self.store._generate_settings_file()
        self.assert_original_preserved()
