"""Verify the reviewed payload set without importing macOS or GUI modules."""

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "ci_tooling/components.lock.json"


def verify(root: Path = ROOT) -> dict:
    lock = json.loads((root / "ci_tooling/components.lock.json").read_text())
    tree = ast.parse((root / "opencore_legacy_patcher/constants.py").read_text())
    values = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute) and isinstance(node.value, ast.Constant):
            values[node.target.attr] = node.value.value
    for key, expected in lock["versions"].items():
        if values.get(key) != expected:
            raise ValueError(f"Version differs from reviewed inventory: {key}")
    actual_files = {str(p.relative_to(root)) for p in (root / "payloads").rglob("*") if p.is_file() and (p.suffix in (".zip", ".efi") or str(p.relative_to(root)) in ("payloads/OpenCore/macserial", "payloads/OpenCore/ocvalidate"))}
    if actual_files != set(lock["files"]):
        raise ValueError(f"Payload inventory changed: {actual_files.symmetric_difference(lock['files'])}")
    for name, expected in lock["files"].items():
        path = root / name
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"SHA-256 mismatch: {name}")
        if path.suffix == ".zip":
            with ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f"Corrupt archive: {name}")
                for entry in archive.infolist():
                    parts = PurePosixPath(entry.filename)
                    if parts.is_absolute() or ".." in parts.parts or "\\" in entry.filename:
                        raise ValueError(f"Unsafe archive member: {entry.filename}")
    return lock


if __name__ == "__main__":
    inventory = verify()
    print(f"Verified {len(inventory['files'])} payloads, version declarations and ZIP integrity")
