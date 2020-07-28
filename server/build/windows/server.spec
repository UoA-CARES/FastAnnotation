# -*- mode: python ; coding: utf-8 -*-

import os
block_cipher = None

spec_root = os.path.abspath(SPECPATH)
server_root = os.path.join(spec_root, "..", "..")

a = Analysis([os.path.join(server_root, "app.py")],
             pathex=[server_root],
             binaries=[],
             datas=[],
             hiddenimports=["mysql.connector.locales.eng"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='fastannotation_server',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )


# Copy config file to output location
import shutil
shutil.copyfile(os.path.join(server_root, "config.ini"), os.path.join(DISTPATH, "config.ini"))

# Check Platform
from sys import platform

output = "fastannotation_server_"
if platform.startswith('win32') or platform.startswith('cygwin'):
    output += "win"
elif platform.startswith('linux'):
    output += "linux"
elif platform.startswith('darwin'):
    output += "mac"
else:
    output += "unknown"

# Create target zip
shutil.make_archive(output, "zip", DISTPATH)
