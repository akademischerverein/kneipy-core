#!/usr/bin/env python

import glob
import os

from setuptools import find_packages

try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))

try:
    with open(os.path.join(here, 'README.md')) as f:
        README = f.read()
except FileNotFoundError:
    # this happens if renovate tries to parse this file
    README = ""

REQUIREMENTS = [
    'SQLAlchemy>=1.4.0,<2',
    'psycopg2-binary>=2.7.3.1',
    'alembic>=0.9.5',
    'attrs',
    # Unittest-Framework
    'nose',
    'coverage',
]

setup(
    name='kneipy-core',
    version='0.0.0-dev0',
    description='',
    long_description=README,
    author='Jens Gutermuth',
    author_email='jens@gutermuth-online.de',
    install_requires=REQUIREMENTS,
    keywords=[],
    packages=find_packages(),
    data_files=[
        ('lib/kneipy/core-migrations',
            glob.glob('migrations/versions/*.py'))
    ],
    include_package_data=True,
    classifiers=[
    ],
    entry_points={
    },
)
