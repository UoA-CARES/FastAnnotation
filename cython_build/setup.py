from setuptools import setup, Extension
from Cython.Distutils import build_ext
import numpy as np

# Template taken from https://github.com/thearn/simple-cython-example
NAME = "fast-annotation-cython-core"
VERSION = "0.1"
DESCR = "A collection of utility methods optimized in cython"
REQUIRES = ['numpy', 'cython']

AUTHOR = "Arran Davis"
EMAIL = "arran94@gmail.com"

LICENSE = "Apache 2.0"

SRC_DIR = "cython_util"
PACKAGES = [SRC_DIR]

ext_1 = Extension(SRC_DIR + ".utils",
                  [SRC_DIR + "/utils.pyx"],
                  libraries=[],
                  include_dirs=[np.get_include()])


EXTENSIONS = [ext_1]

if __name__ == "__main__":
    setup(install_requires=REQUIRES,
          packages=PACKAGES,
          zip_safe=False,
          name=NAME,
          version=VERSION,
          description=DESCR,
          author=AUTHOR,
          author_email=EMAIL,
          license=LICENSE,
          cmdclass={"build_ext": build_ext},
          ext_modules=EXTENSIONS
          )
