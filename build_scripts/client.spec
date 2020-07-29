# -*- mode: python -*-
import shutil
import os
from sys import platform

block_cipher = None

shutil.rmtree(DISTPATH, ignore_errors=True)
os.mkdir(DISTPATH)

spec_root = os.path.abspath(SPECPATH)
client_root = os.path.join(spec_root, "..", "client")
config_file = os.path.join(client_root, "config.ini")

# Copy config file to build and target locations
shutil.copyfile(config_file, os.path.join(spec_root, "config.ini"))
shutil.copyfile(config_file, os.path.join(DISTPATH, "config.ini"))


a = Analysis([os.path.join(client_root, "annotation_client.py")],
             pathex=[client_root],
             binaries=None,
             datas=None,
             hiddenimports=['scipy.special.cython_special', 'skimage.feature._orb_descriptor_positions'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tornado'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
         cipher=block_cipher)


extra_deps = []
if platform.startswith('win32') or platform.startswith('cygwin'):
    from kivy_deps import sdl2, glew
    extra_deps = [Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]

exe = EXE(pyz, Tree(os.path.join(client_root, "data"), os.path.join("client", "data")),
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          *extra_deps,
          name='fastannotation_client',
          debug=False,
          strip=False,
          upx=True,
          console=True)

# Check Platform
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

# Clean up
shutil.rmtree(workpath)
os.remove(os.path.join(os.path.join(spec_root, "config.ini")))
