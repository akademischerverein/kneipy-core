#!/usr/bin/env python

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

REQUIREMENTS = [
    'SQLAlchemy==1.2.0b2',
    'psycopg2>=2.7.3.1',
    'alembic>=0.9.5',
    # Unittest-Framework
    'nose',
    'coverage',
]

setup(
    name='kneipy-core',
    version='0.0.0pre-alpha',
    description='',
    long_description=README,
    author='Jens Gutermuth',
    author_email='jens@gutermuth-online.de',
    install_requires=REQUIREMENTS,
    keywords=[],
    packages=find_packages(),
    classifiers=[
    ],
    entry_points={
    },
)
