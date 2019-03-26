#!/usr/bin/env python
"""glr"""
from os import path

from setuptools import find_packages, setup

# read the contents of your README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='glr',
    version='1.0.1',
    author='Jens Langhammer',
    author_email='jens@beryju.org',
    url='https://github.com/BeryJu/glr',
    description='Locally run your gitlab-ci.yml scripts',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    packages=['.'],
    install_requires=['pyyaml'],
    entry_points={
        'console_scripts': [
            'glr = glr:entrypoint',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
