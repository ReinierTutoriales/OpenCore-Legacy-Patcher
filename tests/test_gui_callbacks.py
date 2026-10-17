"""Run real GUI callbacks against controls destroyed before event dispatch."""

import ast
import logging
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


class Control:
    def __init__(self):
        self.destroyed = False
        self.deleting = False
        self.values = []

    def __bool__(self):
        return not self.destroyed

    def IsBeingDeleted(self):
        return self.deleting

    def AppendText(self, value):
        if self.destroyed or self.deleting:
            raise RuntimeError("wrapped C/C++ object has been deleted")
        self.values.append(value)

    SetValue = AppendText


class CallbackTests(unittest.TestCase):
    def setUp(self):
        self.pending = []
        self.control = Control()
        self.wx = types.SimpleNamespace(TextCtrl=object, Gauge=object, CallAfter=lambda callback, *args: self.pending.append((callback, args)))

    def load_class(self, name, **namespace):
        path = Path(__file__).resolve().parents[1] / "opencore_legacy_patcher/wx_gui/gui_support.py"
        tree = ast.parse(path.read_text())
        node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
        namespace.update(wx=self.wx, logging=logging, constants=types.SimpleNamespace(Constants=object))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
        return namespace[name]

    def dispatch(self):
        for callback, args in self.pending:
            callback(*args)

    def emit_log(self):
        handler = self.load_class("ThreadHandler")(self.control)
        handler.emit(logging.LogRecord("test", logging.INFO, "", 0, "message", (), None))
        self.assertEqual(self.control.values, [])

    def pulse(self):
        worker = self.load_class("GaugePulseCallback", time=types.SimpleNamespace(sleep=lambda _: setattr(worker, "pulse_thread_active", False)))
        worker = worker.__new__(worker)
        worker.gauge = self.control
        worker.gauge_value = 0
        worker.max_value = 100
        worker.pulse_forward = True
        worker.pulse_thread_active = True
        worker._pulse()
        return worker

    def test_live_log_control_receives_text_on_dispatch(self):
        self.emit_log()
        self.dispatch()
        self.assertEqual(self.control.values, ["message\n"])

    def test_log_queued_before_control_destruction_is_discarded(self):
        self.emit_log()
        self.control.destroyed = True
        self.dispatch()
        self.assertEqual(self.control.values, [])

    def test_log_is_discarded_while_control_is_being_deleted(self):
        self.emit_log()
        self.control.deleting = True
        self.dispatch()
        self.assertEqual(self.control.values, [])

    def test_queued_pulse_does_not_update_a_stopped_animation(self):
        self.pulse()
        self.dispatch()
        self.assertEqual(self.control.values, [])

    def test_queued_pulse_does_not_access_a_destroyed_gauge(self):
        worker = self.pulse()
        worker.pulse_thread_active = True
        self.control.destroyed = True
        self.dispatch()
        self.assertEqual(self.control.values, [])

    def test_live_animation_keeps_existing_progress_value(self):
        worker = self.pulse()
        worker.pulse_thread_active = True
        self.dispatch()
        self.assertEqual(self.control.values, [1])
