import plistlib
import subprocess
import types
import unittest
from unittest.mock import Mock

from method_loader import load_method


class RootDiskIdentifierTests(unittest.TestCase):
    def test_snapshot_suffix_is_removed_without_damaging_volume_identifier(self):
        for identifier, snapshot, expected in [("disk1s5s1", True, "disk1s5"), ("disk12s25s12", True, "disk12s25"), ("disk123s456s123", True, "disk123s456"), ("disk12s25", False, "disk12s25")]:
            with self.subTest(identifier=identifier):
                result = subprocess.CompletedProcess([], 0, plistlib.dumps({"DeviceIdentifier": identifier, "APFSSnapshot": snapshot}))
                namespace = {"plistlib": plistlib, "subprocess": types.SimpleNamespace(run=Mock(return_value=result))}
                method = load_method("opencore_legacy_patcher/sys_patch/mount/mount.py", "RootVolumeMount", "_fetch_root_volume_identifier", namespace)
                self.assertEqual(method(object()), expected)
