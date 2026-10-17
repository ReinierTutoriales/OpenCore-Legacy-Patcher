"""Stage and verify an EFI before replacing managed boot files.

Backups remain on the ESP. This supports rollback after an I/O failure;
it cannot make multiple FAT directory renames atomic across a power failure.
"""

import hashlib
import json
import shutil
import uuid
from pathlib import Path


MANAGED_PATHS = ("EFI/OC", "System", "boot.efi", "EFI/BOOT")


def _inventory(path: Path) -> dict[str, str]:
    if path.is_symlink():
        raise ValueError(f"Symbolic links are not allowed in boot files: {path}")
    if path.is_file():
        with path.open("rb") as stream:
            return {".": hashlib.file_digest(stream, "sha256").hexdigest()}
    result = {}
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"Symbolic links are not allowed in boot files: {item}")
        if item.is_file():
            with item.open("rb") as stream:
                result[str(item.relative_to(path))] = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def _copy_verified(source: Path, destination: Path) -> None:
    expected = _inventory(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)
    if _inventory(destination) != expected:
        raise OSError(f"Verification failed: {destination}")


def install_efi(source: Path, mount: Path, boot_efi: bool = False) -> Path:
    """Install managed files, preserving the old files and unrelated EFI loaders.

    Returns the backup directory. If rollback fails, preserve the lock and
    journal so another installation cannot overwrite recovery information.
    """
    source, mount = Path(source), Path(mount)
    for required in ("EFI/OC/OpenCore.efi", "EFI/OC/config.plist", "System/Library/CoreServices/boot.efi"):
        if not (source / required).is_file():
            raise ValueError(f"Incomplete EFI build: {required}")
    if mount.is_symlink() or not mount.is_dir():
        raise ValueError("EFI mount point must be an existing directory")
    if source.resolve().is_relative_to(mount.resolve()):
        raise ValueError("Build source must be outside the target EFI")
    paths = MANAGED_PATHS if boot_efi else MANAGED_PATHS[:-1]
    for name in (*paths, ".OCLP-Backups", "EFI"):
        path = mount / name
        for parent in (path, *path.parents):
            if parent == mount.parent:
                break
            if parent.is_symlink():
                raise ValueError(f"Unsafe EFI destination: {parent}")
    required_bytes = sum(p.stat().st_size for p in source.rglob("*") if p.is_file())
    if shutil.disk_usage(mount).free < required_bytes + 1024 * 1024:
        raise OSError("Insufficient free space to stage the EFI")

    lock = mount / ".OCLP-install.lock"
    lock.mkdir()  # Atomic exclusion of another installer; never remove a stale lock silently.
    token = uuid.uuid4().hex
    stage = mount / f".OCLP-Staging-{token}"
    backup = mount / ".OCLP-Backups" / token
    moved, installed = [], []
    release_lock = True
    try:
        stage.mkdir()
        for name in ("EFI/OC", "System", "boot.efi"):
            if (source / name).exists():
                _copy_verified(source / name, stage / name)
        if boot_efi:
            (stage / "EFI/BOOT").mkdir(parents=True)
            (stage / "System/Library/CoreServices/boot.efi").rename(stage / "EFI/BOOT/BOOTx64.efi")
            shutil.rmtree(stage / "System")

        backup.mkdir(parents=True)
        journal = {"paths": list(paths), "previous": [p for p in paths if (mount / p).exists()], "state": "prepared"}
        (backup / "transaction.json").write_text(json.dumps(journal, indent=2))
        try:
            for name in paths:
                old = mount / name
                if old.exists():
                    saved = backup / name
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    old.rename(saved)
                    moved.append(name)
                new = stage / name
                if new.exists():
                    old.parent.mkdir(parents=True, exist_ok=True)
                    new.rename(old)
                    installed.append(name)
            for name in installed:
                # Detect corrupt writes/renames before reporting success.
                if name == "EFI/BOOT":
                    expected = _inventory(source / "System/Library/CoreServices/boot.efi")
                    actual = _inventory(mount / "EFI/BOOT/BOOTx64.efi")
                else:
                    expected, actual = _inventory(source / name), _inventory(mount / name)
                if expected != actual:
                    raise OSError(f"Installed EFI verification failed: {name}")
            journal["state"] = "complete"
            (backup / "transaction.json").write_text(json.dumps(journal, indent=2))
        except BaseException:
            try:
                for name in reversed(installed):
                    target = mount / name
                    shutil.rmtree(target) if target.is_dir() else target.unlink()
                for name in reversed(moved):
                    (backup / name).rename(mount / name)
                journal["state"] = "rolled_back"
                (backup / "transaction.json").write_text(json.dumps(journal, indent=2))
            except BaseException as error:
                release_lock = False
                raise OSError(f"EFI rollback failed. Preserve {backup} and {lock} for recovery") from error
            raise
        return backup
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        if release_lock:
            lock.rmdir()
