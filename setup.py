#!/usr/bin/env python3
from distutils.core import setup

setup(
    name='pydgeot',
    version='0.3',
    packages=[
        'pydgeot',
        'pydgeot.app',
        'pydgeot.utils',
        'pydgeot.commands',
        'pydgeot.commands.builtins',
        'pydgeot.processors',
        'pydgeot.processors.builtins'],
    scripts=['scripts/pydgeot'],
    requires=['docopt'],
    url='https://github.com/broiledmeat/pydgeot',
    license='Apache License, Version 2.0',
    author='Derrick Staples',
    author_email='broiledmeat@gmail.com',
    description='Static content generator'
)
