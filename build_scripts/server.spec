# -*- mode: python ; coding: utf-8 -*-

import shutil
import os
from sys import platform
block_cipher = None

shutil.rmtree(DISTPATH, ignore_errors=True)
os.mkdir(DISTPATH)

spec_root = os.path.abspath(SPECPATH)
server_root = os.path.join(spec_root, "..", "server")
config_file = os.path.join(server_root, "config.ini")

# Copy config file to build and target locations
shutil.copyfile(config_file, os.path.join(spec_root, "config.ini"))
shutil.copyfile(config_file, os.path.join(DISTPATH, "config.ini"))

a = Analysis([os.path.join(server_root, "app.py")],
             pathex=[server_root],
             binaries=[],
             datas=[],
             hiddenimports=["pkg_resources", "mysql.connector.locales.eng"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          Tree(os.path.join(server_root, "data"), os.path.join("server", "data")),
          a.scripts,
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

# Check Platform
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

# Clean up
shutil.rmtree(workpath)
os.remove(os.path.join(os.path.join(spec_root, "config.ini")))