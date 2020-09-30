#!/usr/bin/env python
from setuptools import setup

setup(
      name='tap-sumologic',
      version='0.1.0',
      description='Singer.io tap for extracting Sumologic search results.',
      author='P.A. Masse',
      url='http://www.split.io',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['tap_sumologic'],
      install_requires=[
            'singer-python>=5.0.12',
            'requests',
            'pendulum',
            'sumologic-sdk',
            'ujson',
            'voluptuous==0.10.5'
      ],
      entry_points='''
            [console_scripts]
            tap-sumologic=tap_sumologic:main
      ''',
      packages=['tap_sumologic']
)
