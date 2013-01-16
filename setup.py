#!/usr/bin/env python
from distutils.core import setup

setup(
    name='pydgeot',
    version='0.2',
    packages=['pydgeot', 'pydgeot.processors', 'pydgeot.processors.builtins', 'pydgeot.commands', 'pydgeot.commands.builtins'],
    scripts=['scripts/pydgeot'],
    url='https://github.com/broiledmeat/pydgeot',
    license='Apache License, Version 2.0',
    author='Derrick Staples',
    author_email='broiledmeat@gmail.com',
    description='Static content generator'
)
