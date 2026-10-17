import logging
import traceback
import types
import unittest
from unittest.mock import MagicMock, Mock, patch

from method_loader import load_method


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger()
        self.saved_handlers = self.logger.handlers[:]
        self.addCleanup(setattr, self.logger, "handlers", self.saved_handlers)
        # The convenience logging.info function configures a root handler if none exists.
        info = patch.object(logging, "info")
        info.start()
        self.addCleanup(info.stop)
        self.worker = types.SimpleNamespace(text_box=object(), result=True, build_successful=True, constants=types.SimpleNamespace(custom_model="MacPro5,1", computer=types.SimpleNamespace(real_model="MacPro5,1")))
        self.namespace = {"logging": logging, "traceback": traceback, "gui_support": types.SimpleNamespace(ThreadHandler=Mock(side_effect=lambda box: logging.NullHandler()))}

    def test_install_failure_clears_previous_success_and_preserves_handlers(self):
        for count in (0, 1, 3):
            with self.subTest(existing_handlers=count):
                handlers = [logging.NullHandler() for _ in range(count)]
                self.logger.handlers = handlers[:]
                self.worker.result = True
                self.namespace["install"] = types.SimpleNamespace(tui_disk_installation=Mock(side_effect=OSError("mount failed")))
                method = load_method("opencore_legacy_patcher/wx_gui/gui_install_oc.py", "InstallOCFrame", "_install_oc", self.namespace)
                method(self.worker, "disk2s1")
                self.assertFalse(self.worker.result)
                self.assertEqual(self.logger.handlers, handlers)

    def test_build_failure_clears_previous_success_and_preserves_handlers(self):
        self.logger.handlers = []
        self.namespace["build"] = types.SimpleNamespace(BuildOpenCore=Mock(side_effect=OSError("build failed")))
        method = load_method("opencore_legacy_patcher/wx_gui/gui_build.py", "BuildFrame", "_build", self.namespace)
        method(self.worker)
        self.assertFalse(self.worker.build_successful)
        self.assertEqual(self.logger.handlers, [])

    def test_root_patch_workers_remove_only_their_own_handler_on_failure(self):
        for method_name in ("_start_root_patching", "_revert_root_patching"):
            with self.subTest(method=method_name):
                handlers = [logging.NullHandler() for _ in range(4)]
                self.logger.handlers = handlers[:]
                self.namespace["sys_patch"] = types.SimpleNamespace(PatchSysVolume=Mock(side_effect=OSError("patch failed")))
                method = load_method("opencore_legacy_patcher/wx_gui/gui_sys_patch_start.py", "SysPatchStartFrame", method_name, self.namespace)
                method(self.worker, {})
                self.assertEqual(self.logger.handlers, handlers)

    def test_accepting_root_patch_prompt_does_not_show_it_again(self):
        wx = MagicMock()
        wx.YES_NO, wx.YES_DEFAULT, wx.ID_YES = 1, 2, 3
        dialog = wx.MessageDialog.return_value
        dialog.GetReturnCode.return_value = wx.ID_YES
        stages = types.SimpleNamespace(INACTIVE=0, UNPATCHING=4)
        gui_support = types.SimpleNamespace(AutoUpdateStages=stages, wait_for_thread=Mock())
        patch_display = Mock()
        namespace = {"wx": wx, "threading": types.SimpleNamespace(Thread=Mock()), "gui_support": gui_support, "os_data": types.SimpleNamespace(os_data=types.SimpleNamespace(big_sur=20)), "gui_sys_patch_display": patch_display}
        method = load_method("opencore_legacy_patcher/wx_gui/gui_install_oc.py", "InstallOCFrame", "_invoke_install_oc", namespace)
        self.worker.constants.update_stage = 1
        self.worker.constants.detected_os = 25
        self.worker.title = "Install"
        for name in ("_install_oc", "Hide", "GetPosition", "Destroy"):
            setattr(self.worker, name, Mock())
        method(self.worker, "disk2s1")
        dialog.ShowModal.assert_called_once()
        patch_display.SysPatchDisplayFrame.assert_called_once()
        self.worker.Destroy.assert_called_once()
