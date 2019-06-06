# -*- coding: utf-8 -*-
#setup.py file
from setuptools import setup


setup(
      name = 'ecogVIS',
      version = '0.0.1',
      description = 'python gui interface',
      author = 'Luiz Tauffer and Ben Dichter',
      email = 'ben.dichter@gmail.com',
      scripts = ['ecog_vis.py'],
      url = '',
      install_requires = ['PyQt5', 'matplotlib', 'cycler', 'scipy', 'numpy', 'h5py', 'pyqtgraph', 'pandas', 'pynwb',
                          'nwbext_ecog', 'pyopengl',
                          'ecog @ git+https://github.com/luiztauffer/process_ecog.git@docker#egg=ecog'],
      #dependency_links=['http://github.com/luiztauffer/process_ecog/tarball/docker#egg=ecog'],
      )

#ecog @ git+ssh://git@github.com/luiztauffer/process_ecog.git@docker
#ecog @ git+https://github.com/luiztauffer/process_ecog.git@docker#egg=ecog
