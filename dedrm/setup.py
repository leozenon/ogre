#! /usr/bin/env python

import dedrm

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

packages = [
    'dedrm',
]

setup(
    name='dedrm',
    version=dedrm.PLUGIN_VERSION,
    description='Apprentice Alf\'s DRM Tools',
    long_description='Apprentice Alf\'s DRM Tools',
    author='',
    author_email='',
    url='',
    packages=['dedrm'],
    package_data={'': []},
    package_dir={'': '.'},
    include_package_data=True,
)
