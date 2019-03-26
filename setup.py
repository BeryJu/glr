#!/usr/bin/env python
"""glr"""
from setuptools import find_packages, setup

setup(
    name='glr',
    version='1.0.0',
    author='Jens Langhammer',
    author_email='jens@beryju.org',
    url='https://github.com/BeryJu/glr',
    description='Locally run your gitlab-ci.yml scripts',
    license='MIT',
    packages=['.'],
    install_requires=['pyyaml'],
    entry_points={
        'console_scripts': [
            'glr = glr:main',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
