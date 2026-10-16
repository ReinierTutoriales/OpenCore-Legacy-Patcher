"""Load actual methods without importing wxPython or probing the host Mac."""

import ast
from pathlib import Path


def load_method(relative_path, class_name, method_name, namespace):
    path = Path(__file__).resolve().parents[1] / relative_path
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[method_name]
