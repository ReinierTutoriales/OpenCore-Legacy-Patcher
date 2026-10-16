import logging
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

from method_loader import load_method


class ImmediateThread:
    """Finish before the UI waits, reproducing the queued-callback race."""
    def __init__(self, target):
        self.target = target

    def start(self):
        self.target()


class UpdateSequenceTests(unittest.TestCase):
    def test_failed_step_never_reaches_launch_even_before_gui_callbacks_run(self):
        for failed_step in ("extract", "install"):
            with self.subTest(step=failed_step):
                wx = MagicMock()
                wx.DEFAULT_FRAME_STYLE, wx.RESIZE_BORDER, wx.MAXIMIZE_BOX = 1, 2, 4
                gui_support = MagicMock()
                namespace = {"wx": wx, "logging": logging, "Path": Path, "threading": types.SimpleNamespace(Thread=ImmediateThread), "gui_support": gui_support, "gui_download": MagicMock(), "network_handler": MagicMock()}
                namespace["constants"] = types.SimpleNamespace(Constants=object)
                namespace["network_handler"].DownloadObject.return_value.download_complete = True
                method = load_method("opencore_legacy_patcher/wx_gui/gui_update.py", "UpdateFrame", "__init__", namespace)
                worker = types.SimpleNamespace()
                worker._extract_update = Mock(side_effect=lambda: setattr(worker, "update_failed", failed_step == "extract"))
                worker._install_update = Mock(side_effect=lambda: setattr(worker, "update_failed", failed_step == "install"))
                worker._launch_update = Mock()
                parent = MagicMock()
                parent.GetChildren.return_value = []
                constants = types.SimpleNamespace(payload_path=Path("/tmp"), app_icon_path=Path("/tmp/icon.icns"))
                method(worker, parent, "Update", constants, None, "https://example.test/update.pkg", "3.0.0")
                worker._launch_update.assert_not_called()
                if failed_step == "extract":
                    worker._install_update.assert_not_called()
                else:
                    worker._install_update.assert_called_once()

    def test_installer_failure_is_reported_before_queued_exit_callback(self):
        wx = MagicMock()
        wx.OK, wx.ICON_ERROR, wx.ICON_INFORMATION = 1, 2, 4
        wrapper = Mock()
        wrapper.run_as_root.return_value = subprocess.CompletedProcess([], 1, b"", b"installation failed")
        namespace = {"wx": wx, "sys": sys, "logging": logging, "subprocess_wrapper": wrapper, "subprocess": Mock()}
        method = load_method("opencore_legacy_patcher/wx_gui/gui_update.py", "UpdateFrame", "_install_update", namespace)
        worker = types.SimpleNamespace(pkg_download_path="/tmp/update.pkg", progress_bar_animation=Mock(), progress_bar=Mock(), update_failed=False)
        method(worker)
        self.assertTrue(worker.update_failed)
        self.assertTrue(wx.CallAfter.called)

    def test_successful_installer_clears_failure_state(self):
        wrapper = Mock()
        wrapper.run_as_root.return_value = subprocess.CompletedProcess([], 0, b"", b"")
        method = load_method("opencore_legacy_patcher/wx_gui/gui_update.py", "UpdateFrame", "_install_update", {"subprocess_wrapper": wrapper, "logging": logging})
        worker = types.SimpleNamespace(pkg_download_path="/tmp/update.pkg", update_failed=True)
        method(worker)
        self.assertFalse(worker.update_failed)
