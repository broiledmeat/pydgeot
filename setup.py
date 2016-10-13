#!/usr/bin/env python3
import sys
import setuptools
from distutils.core import setup

if sys.version_info < (3, 3):
    print('Sorry, Pydgeot requires Python 3.3+')
    exit(1)

base_package = 'pydgeot'

version = __import__('pydgeot').__version__
packages = [base_package] + ['{}.{}'.format(base_package, package)
                             for package in setuptools.find_packages(base_package)]

setup(
    name='pydgeot',
    description='Plugin based static content generator',
    url='https://github.com/broiledmeat/pydgeot',
    license='Apache License, Version 2.0',
    author='Derrick Staples',
    author_email='broiledmeat@gmail.com',
    version=version,
    packages=packages,
    scripts=['scripts/pydgeot'],
    requires=['docopt'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
