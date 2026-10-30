import logging
import types
import unittest
from unittest.mock import Mock

from method_loader import load_method


class NotificationTests(unittest.TestCase):
    def check_notification(self, response, failure=False):
        dialog = Mock()
        timer = Mock()
        wx = types.SimpleNamespace(YES_NO=1, ICON_INFORMATION=2, ID_YES=3, ID_NO=4, ID_CANCEL=5,
                                   MessageDialog=Mock(return_value=dialog), CallLater=Mock(return_value=timer))
        if failure:
            dialog.ShowModal.side_effect = RuntimeError("dialog failed")
        elif response == "timeout":
            def expire():
                _, callback, result = wx.CallLater.call_args.args
                callback(result)
                return result
            dialog.ShowModal.side_effect = expire
        else:
            dialog.ShowModal.return_value = response
        namespace = {"wx": wx, "logging": logging, "threading": types.SimpleNamespace(Thread=Mock(side_effect=AssertionError("UI must stay on the main thread")))}
        method = load_method("opencore_legacy_patcher/wx_gui/gui_cache_os_update.py", "OSUpdateFrame", "_notifyUser", namespace)
        frame = types.SimpleNamespace(frame=object(), os_data=("15.0", "24A"), did_cancel=-1, _notifyUserThread=Mock())
        if failure:
            with self.assertRaisesRegex(RuntimeError, "dialog failed"):
                method(frame)
        else:
            method(frame)
            self.assertEqual(frame.did_cancel, int(response not in (wx.ID_YES, "timeout")))
            if response == "timeout":
                dialog.EndModal.assert_called_once_with(wx.ID_YES)
        wx.CallLater.assert_called_once_with(10000, dialog.EndModal, wx.ID_YES)
        timer.Stop.assert_called_once()
        dialog.Destroy.assert_called_once()

    def test_accept(self):
        self.check_notification(3)

    def test_timeout_continues_after_the_existing_ten_second_window(self):
        self.check_notification("timeout")

    def test_cancel_and_close(self):
        for response in (4, 5):
            with self.subTest(response=response):
                self.check_notification(response)

    def test_failure_still_cleans_timer_and_dialog(self):
        self.check_notification(None, failure=True)
