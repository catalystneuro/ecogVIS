# -*- coding: utf-8 -*-
#setup.py file
from setuptools import setup, find_packages

setup(name = 'ecogvis',
      version = '1.0.1',
      description = 'ecog gui interface for python',
      author = 'Luiz Tauffer and Ben Dichter',
      email = 'ben.dichter@gmail.com',
      #scripts = ['ecog_vis.py'],
      #url = '',
      packages=find_packages(),
      include_package_data = True,
      #install_requires = ['PyQt5', 'matplotlib', 'cycler', 'scipy', 'numpy',
    #                      'h5py', 'pyqtgraph', 'pandas', 'pynwb',
    #                      'nwbext_ecog', 'pyopengl'],
      #dependency_links=['http://github.com/luiztauffer/process_ecog/tarball/docker#egg=ecog'],
      )

#ecog @ git+ssh://git@github.com/luiztauffer/process_ecog.git@docker
#ecog @ git+https://github.com/luiztauffer/process_ecog.git@docker#egg=ecog
