#!/usr/bin/env python

import os
import glob

from setuptools import find_packages

try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

REQUIREMENTS = [
    'SQLAlchemy==1.2.0b2',
    'psycopg2-binary>=2.7.3.1',
    'alembic>=0.9.5',
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
        ('lib/kneipy/core-migrations', [
            'alembic.ini'
        ] + glob.glob('migrations/versions/*.py'))
    ],
    include_package_data=True,
    classifiers=[
    ],
    entry_points={
    },
)
