"""
updates.py: Check for OpenCore Legacy Patcher binary updates

Call check_binary_updates() to determine if any updates are available
Returns dict with Link and Version of the latest binary update if available
"""

import logging

from typing import Optional, Union
from packaging import version

from . import network_handler

from .. import constants


class CheckBinaryUpdates:
    def __init__(self, global_constants: constants.Constants) -> None:
        self.constants: constants.Constants = global_constants
        try:
            self.binary_version = version.parse(self.constants.patcher_version)
        except version.InvalidVersion:
            assert self.constants.special_build is True, "Invalid version number for binary"
            # Special builds will not have a proper version number
            self.binary_version = version.parse("0.0.0")

        self.latest_details = None

    def check_if_newer(self, version: Union[str, version.Version]) -> bool:
        """
        Check if the provided version is newer than the local version

        Parameters:
            version (str): Version to compare against

        Returns:
            bool: True if the provided version is newer, False if not
        """
        if self.constants.special_build is True:
            return False

        return self._check_if_build_newer(version, self.binary_version)

    def _check_if_build_newer(self, first_version: Union[str, version.Version], second_version: Union[str, version.Version]) -> bool:
        """
        Check if the first version is newer than the second version

        Parameters:
            first_version_str (str): First version to compare against (generally local)
            second_version_str (str): Second version to compare against (generally remote)

        Returns:
            bool: True if first version is newer, False if not
        """

        if not isinstance(first_version, version.Version):
            try:
                first_version = version.parse(first_version)
            except version.InvalidVersion:
                # Special build > release build: assume special build is newer
                return True

        if not isinstance(second_version, version.Version):
            try:
                second_version = version.parse(second_version)
            except version.InvalidVersion:
                # Release build > special build: assume special build is newer
                return False

        if first_version == second_version:
            if not self.constants.commit_info[0].startswith("refs/tags"):
                # Check for nightly builds
                return True

        return first_version > second_version


    def check_binary_updates(self) -> Optional[dict]:
        """
        Check if any updates are available for the OpenCore Legacy Patcher binary

        Returns:
            dict: Dictionary with Link and Version of the latest binary update if available
        """

        if self.constants.special_build is True:
            # Special builds do not get updates through the updater
            return None

        if self.latest_details:
            # We already checked
            return self.latest_details

        repo = self.constants.repo_link.removeprefix("https://github.com/").rstrip("/")
        url = f"https://api.github.com/repos/{repo}/releases"
        try:
            response = network_handler.NetworkUtilities().get(url, timeout=(5, 15))
            response.raise_for_status()
            releases = response.json()
            if not isinstance(releases, list):
                return None
            candidates = []
            for release in releases:
                if not isinstance(release, dict) or release.get("draft"):
                    continue
                if release.get("prerelease") and not self.binary_version.is_prerelease:
                    continue
                try:
                    release_version = version.parse(release.get("tag_name", ""))
                except (version.InvalidVersion, TypeError):
                    continue
                if release_version.is_prerelease and not self.binary_version.is_prerelease:
                    continue
                if not isinstance(release.get("assets"), list):
                    continue
                if any(self._valid_package(asset) for asset in release["assets"]):
                    candidates.append((release_version, release))
            if not candidates:
                return None
            _, data_set = max(candidates, key=lambda item: item[0])
        except (ValueError, network_handler.requests.exceptions.RequestException) as error:
            logging.warning("Unable to check patcher updates: %s", error)
            return None

        # The release marked as latest will always be stable, and thus, have a proper version number
        # But if not, let's not crash the program
        try:
            latest_remote_version = version.parse(data_set["tag_name"])
        except version.InvalidVersion:
            return None

        if not self._check_if_build_newer(latest_remote_version, self.binary_version):
            return None

        for asset in data_set["assets"]:
            if self._valid_package(asset):
                self.latest_details = {
                    "Name": asset["name"],
                    "Version": latest_remote_version,
                    "Link": asset.get("browser_download_url", ""),
                    "Github Link": f"{self.constants.repo_link}/releases/tag/{data_set['tag_name']}",
                }
                return self.latest_details

        return None

    def _valid_package(self, asset) -> bool:
        return (
            isinstance(asset, dict)
            and asset.get("name") == "OpenCore-Patcher.pkg"
            and isinstance(asset.get("browser_download_url"), str)
            and asset["browser_download_url"].startswith(f"{self.constants.repo_link}/releases/download/")
        )
