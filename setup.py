# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.md', 'r') as f:
    long_description = f.read()

setup(name = 'ecogVIS',
      version = '1.0.0',
      description = 'Timeseries visualizer for Electrocorticography (ECoG) signals stored in NWB files.',
      long_description = long_description,
      long_description_content_type = 'text/markdown',
      author = 'Luiz Tauffer and Ben Dichter',
      email = 'ben.dichter@gmail.com',
      packages=find_packages(),
      include_package_data = True,
      install_requires = ['PyQt5', 'matplotlib', 'cycler', 'scipy', 'numpy',
                          'h5py', 'pyqtgraph', 'pandas', 'pynwb',
<<<<<<< HEAD
                          'nwbext_ecog', 'ndx-spectrum', 'pyopengl'],
=======
                          'ndx_ecog', 'pyopengl'],
>>>>>>> da45d2dd2f6d61f0a900ddef1d4252b9cba06507
      )
