# -*- mode: python -*-

from kivy_deps import sdl2, glew

block_cipher = None


a = Analysis(['..\\..\\annotation_client.py'],
             pathex=['..\\..'],
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


exe = EXE(pyz, Tree('..\\..\\data','client\\data'),
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
          name='fastannotation',
          debug=False,
          strip=False,
          upx=True,
          console=True)


# Copy config file to output location
import shutil
shutil.copyfile('..\\..\\config.ini', '{0}/config.ini'.format(DISTPATH))