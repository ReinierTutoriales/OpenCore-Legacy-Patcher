import logging
import traceback
import types
import unittest
from unittest.mock import Mock, patch

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
