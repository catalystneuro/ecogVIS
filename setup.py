# -*- coding: utf-8 -*-
#setup.py file
from setuptools import setup
setup(
      name = 'ecogTSGUI',
      version = '1.0',
      description = 'python gui interface',
      author = 'Ben Ditcher',
      email = 'xyz@gmail.com',
      scripts = ['ecog_ts_gui.py'],
      url = '',
      install_requires = ['PyQt5', 'matplotlib', 'cycler', 'scipy', 'numpy', 'h5py', 'pyqtgraph']
      
      )