# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import time
import platform
import subprocess

from pathlib import Path

from PyInstaller.building.api import PYZ, EXE, COLLECT
from PyInstaller.building.osx import BUNDLE
from PyInstaller.building.build_main import Analysis

sys.path.append(os.path.abspath(os.getcwd()))

from opencore_legacy_patcher import constants

datas = [
   ('payloads.dmg', '.'),
   ('Universal-Binaries.dmg', '.'),
   ('opencore_legacy_patcher/wx_gui/credits.html', 'opencore_legacy_patcher/wx_gui'),
]

if Path("DortaniaInternalResources.dmg").exists():
   datas.append(('DortaniaInternalResources.dmg', '.'))

# En runners de GitHub (setup-python / pip), wxPython suele ser single-arch
# (arm64 o x86_64), no fat/universal2. Forzar universal2 falla con:
# IncompatibleBinaryArchError: ... is not a fat binary!
_machine = platform.machine().lower()
if _machine in ("arm64", "aarch64"):
    _target_arch = "arm64"
elif _machine in ("x86_64", "amd64"):
    _target_arch = "x86_64"
else:
    _target_arch = None  # dejar default de PyInstaller

a = Analysis(['OpenCore-Patcher-GUI.command'],
             pathex=[],
             binaries=[],
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             noarchive=False)

pyz = PYZ(a.pure)
# PyInstaller EXE signature uses positional for scripts list
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='OpenCore-Patcher',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=_target_arch,
          codesign_identity=None,
          entitlements_file=None)

coll = COLLECT(exe,
               a.binaries,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='OpenCore-Patcher')

app = BUNDLE(coll,
             name='OpenCore-Patcher.app',
             icon="payloads/Icon/AppIcons/OC-Patcher.icns",
             bundle_identifier="com.dortania.opencore-legacy-patcher",
             info_plist={
                "CFBundleName": "OpenCore Legacy Patcher",
                "CFBundleVersion": constants.Constants().patcher_version.split("-")[0],
                "CFBundleShortVersionString": constants.Constants().patcher_version.split("-")[0],
                "NSHumanReadableCopyright": constants.Constants().copyright_date,
                "LSMinimumSystemVersion": "10.10.0",
                "NSRequiresAquaSystemAppearance": False,
                "NSHighResolutionCapable": True,
                "Build Date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "BuildMachineOSBuild": subprocess.run(["/usr/bin/sw_vers", "-buildVersion"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode().strip(),
                "NSPrincipalClass": "NSApplication",
                "CFBundleIconName": "oclp",
             })
