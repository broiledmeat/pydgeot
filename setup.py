import os
from setuptools import setup

setup(
    name = 'pydgeot',
    version = '1205',
    description = 'Static content generator',
    author = 'Derrick Staples',
    author_email = 'broiledmeat@gmail.com',
    license = 'BSD',
    url = 'http://packages.python.org/pydgeot',
    packages=['pydgeot'],
    scripts=['scripts/pydgeot-server', 'scripts/pydgeot-gen', 'scripts/pydgeot-file'],
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.2',
        'Development Status :: 4 - Beta',
        'Environment :: Console'
        'Topic :: Software Development',
        'Topic :: Software Development :: Build Tools',
    ],
)