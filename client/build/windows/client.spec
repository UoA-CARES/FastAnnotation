# -*- mode: python -*-

import os
from kivy_deps import sdl2, glew

block_cipher = None

spec_root = os.path.abspath(SPECPATH)
client_root = os.path.join(spec_root, "..", "..")

a = Analysis([os.path.join(client_root, "annotation_client.py")],
             pathex=[client_root],
             binaries=None,
             datas=None,
             hiddenimports=['scipy.special.cython_special', 'skimage.feature._orb_descriptor_positions'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
         cipher=block_cipher)

exe = EXE(pyz, Tree(os.path.join(client_root, "data"), os.path.join("client", "data")),
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
          name='fastannotation_client',
          debug=False,
          strip=False,
          upx=True,
          console=True)


# Copy config file to output location
import shutil
shutil.copyfile('..\\..\\config.ini', '{0}/config.ini'.format(DISTPATH))

# Check Platform
from sys import platform

output = "fastannotation_client_"
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