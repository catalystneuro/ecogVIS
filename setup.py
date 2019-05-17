# -*- coding: utf-8 -*-
#setup.py file
from setuptools import setup
setup(
      name = 'ecogVIS',
      version = '1.0',
      description = 'python gui interface',
      author = 'Luiz Tauffer and Ben Dichter',
      email = 'ben.dichter@gmail.com',
      scripts = ['ecog_vis.py'],
      url = '',
      install_requires = ['PyQt5', 'matplotlib', 'cycler', 'scipy', 'numpy', 'h5py', 'pyqtgraph', 'pandas']
      
      )
