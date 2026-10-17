"""
global_settings.py: Library for querying and writing global enviroment settings

Alternative to Apple's 'defaults' tool
Store data in '/Users/Shared'
This is to ensure compatibility when running without a user
ie. during automated patching
"""

import logging
import os
import plistlib
import stat
import tempfile

from pathlib import Path


class GlobalEnviromentSettings:
    """
    Library for querying and writing global enviroment settings
    """

    def __init__(self) -> None:
        self.file_name:              str = ".com.dortania.opencore-legacy-patcher.plist"
        self.global_settings_folder: str = "/Users/Shared"
        self.global_settings_plist:  str = f"{self.global_settings_folder}/{self.file_name}"

        self._generate_settings_file()
        self._convert_defaults_to_global_settings()


    def read_property(self, property_name: str) -> str:
        """
        Reads a property from the global settings file
        """

        if Path(self.global_settings_plist).exists():
            try:
                plist = plistlib.load(Path(self.global_settings_plist).open("rb"))
            except Exception as e:
                logging.error("Error: Unable to read global settings file")
                logging.error(e)
                return None
            if property_name in plist:
                return plist[property_name]
        return None

    def _write_settings(self, plist: dict) -> bool:
        """Serialize first, then replace the settings only after a complete write."""
        path = Path(self.global_settings_plist)
        temporary = None
        try:
            data = plistlib.dumps(plist)
            metadata = path.stat()
            with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
                if os.geteuid() == 0:
                    os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            return True
        except (OSError, TypeError, ValueError, OverflowError) as error:
            logging.error("Failed to save global settings: %s", error)
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError as error:
                    logging.warning("Unable to remove temporary settings file: %s", error)


    def delete_property(self, property_name: str) -> None:
        """
        Deletes a property from the global settings file
        """
        if Path(self.global_settings_plist).exists():
            try:
                plist = plistlib.load(Path(self.global_settings_plist).open("rb"))
            except Exception as e:
                logging.error("Error: Unable to read global settings file")
                logging.error(e)
                return
            if property_name in plist:
                del plist[property_name]
                self._write_settings(plist)


    def write_property(self, property_name: str, property_value) -> None:
        """
        Writes a property to the global settings file
        """

        if Path(self.global_settings_plist).exists():
            try:
                plist = plistlib.load(Path(self.global_settings_plist).open("rb"))
            except Exception as e:
                logging.error("Error: Unable to read global settings file")
                logging.error(e)
                return
            plist[property_name] = property_value
            self._write_settings(plist)


    def _generate_settings_file(self) -> None:
        if Path(self.global_settings_plist).exists():
            return
        try:
            with Path(self.global_settings_plist).open("xb") as stream:
                plistlib.dump({"Developed by Dortania": True,}, stream)
        except FileExistsError:
            # Another instance may have created the file after the existence check.
            return
        except PermissionError:
            logging.info("Permission error: Unable to write to global settings file")


    def _convert_defaults_to_global_settings(self) -> None:
        """
        Converts legacy defaults to global settings
        """

        defaults_path = "~/Library/Preferences/com.dortania.opencore-legacy-patcher.plist"
        defaults_path = Path(defaults_path).expanduser()

        if Path(defaults_path).exists():
            # merge defaults with global settings
            try:
                defaults_plist = plistlib.load(Path(defaults_path).open("rb"))
                global_settings_plist = plistlib.load(Path(self.global_settings_plist).open("rb"))
            except Exception as e:
                logging.error("Error: Unable to read global settings file")
                logging.error(e)
                return
            global_settings_plist.update(defaults_plist)
            if not self._write_settings(global_settings_plist):
                return

            # delete defaults plist
            try:
                Path(defaults_path).unlink()
            except Exception as e:
                logging.error("Error: Unable to delete defaults plist")
                logging.error(e)
