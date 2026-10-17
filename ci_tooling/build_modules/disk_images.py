"""
disk_images.py: Fetch and generate disk images (Universal-Binaries.dmg, payloads.dmg)
"""

import hashlib
import json
import subprocess
import urllib.request

from pathlib import Path

from opencore_legacy_patcher import constants
from opencore_legacy_patcher.support import subprocess_wrapper



class GenerateDiskImages:

    def __init__(self, reset_dmg_cache: bool = False) -> None:
        """
        Initialize
        """
        self.reset_dmg_cache = reset_dmg_cache


    def _delete_extra_binaries(self):
        """
        Delete extra binaries from payloads directory
        """

        whitelist_folders = [
            "ACPI",
            "Config",
            "Drivers",
            "Icon",
            "Kexts",
            "OpenCore",
            "Tools",
            "Launch Services",
        ]

        whitelist_files = []

        print("Deleting extra binaries...")
        for file in Path("payloads").glob(pattern="*"):
            if file.is_dir():
                if file.name in whitelist_folders:
                    continue
                print(f"- Deleting {file.name}")
                subprocess_wrapper.run_and_verify(["/bin/rm", "-rf", file])
            else:
                if file.name in whitelist_files:
                    continue
                print(f"- Deleting {file.name}")
                subprocess_wrapper.run_and_verify(["/bin/rm", "-f", file])



    def _generate_payloads_dmg(self):
        """
        Generate disk image containing all payloads
        Disk image will be password protected due to issues with
        Apple's notarization system and inclusion of kernel extensions
        """

        if Path("./payloads.dmg").exists():
            if self.reset_dmg_cache is False:
                print("- payloads.dmg already exists, skipping creation")
                return

            print("- Removing old payloads.dmg")
            subprocess_wrapper.run_and_verify(
                ["/bin/rm", "-rf", "./payloads.dmg"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

        print("Generating DMG...")
        subprocess_wrapper.run_and_verify([
            '/usr/bin/hdiutil', 'create', './payloads.dmg',
            '-megabytes', '32000',  # Overlays can only be as large as the disk image allows
            '-format', 'UDZO', '-ov',
            '-volname', 'OpenCore Patcher Resources (Base)',
            '-fs', 'HFS+',
            '-layout', 'NONE',
            '-srcfolder', './payloads',
            '-passphrase', 'password', '-encryption'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        print("DMG generation complete")


    def _download_resources(self):
        """
        Download required dependencies
        """

        patcher_support_pkg_version = constants.Constants().patcher_support_pkg_version
        required_resources = [
            "Universal-Binaries.dmg"
        ]

        print("Downloading required resources...")
        for resource in required_resources:
            expected = json.loads(Path("ci_tooling/components.lock.json").read_text())["support_package"]
            if expected["version"] != patcher_support_pkg_version:
                raise ValueError("PatcherSupportPkg version does not match the reviewed inventory")
            if Path(f"./{resource}").exists():
                if self.reset_dmg_cache is True:
                    print(f"  - Removing old {resource}")
                    # Just to be safe
                    assert resource, "Resource cannot be empty"
                    assert resource not in ("/", "."), "Resource cannot be root"
                    subprocess_wrapper.run_and_verify(
                        ["/bin/rm", "-rf", f"./{resource}"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                else:
                    with Path(resource).open("rb") as stream:
                        if hashlib.file_digest(stream, "sha256").hexdigest() == expected["sha256"]:
                            print(f"- {resource} already exists and checksum is valid")
                            continue
                    raise ValueError(f"Cached {resource} has an invalid SHA-256")

            print(f"- Downloading {resource}...")

            destination = Path(resource)
            partial = destination.with_suffix(destination.suffix + ".part")
            try:
                digest = hashlib.sha256()
                with urllib.request.urlopen(expected["url"], timeout=30) as response, partial.open("wb") as stream:
                    while chunk := response.read(1024 * 1024):
                        stream.write(chunk)
                        digest.update(chunk)
                if digest.hexdigest() != expected["sha256"]:
                    raise ValueError(f"Downloaded {resource} has an invalid SHA-256")
                partial.replace(destination)
            finally:
                partial.unlink(missing_ok=True)


    def generate(self) -> None:
        """
        Generate disk images
        """

        self._delete_extra_binaries()
        self._generate_payloads_dmg()
        self._download_resources()
