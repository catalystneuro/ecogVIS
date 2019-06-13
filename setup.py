# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(name = 'ecogvis',
      version = '0.0.1',
      description = 'ecog gui interface for python',
      author = 'Luiz Tauffer and Ben Dichter',
      email = 'ben.dichter@gmail.com',
      packages=find_packages(),
      include_package_data = True,
      install_requires = ['PyQt5', 'matplotlib', 'cycler', 'scipy', 'numpy',
                          'h5py', 'pyqtgraph', 'pandas', 'pynwb',
                          'nwbext_ecog', 'pyopengl'],
      )
