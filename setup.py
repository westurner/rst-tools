#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

requirements = [
    'docutils',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='rst-tools',
    version='0.1.0',
    description='Tools for working with ReStructuredText',
    long_description=readme + '\n\n' + history,
    author='Wes Turner',
    author_email='wes@wrd.nu',
    url='https://github.com/westurner/rst-tools',
    packages=[
        'rst-tools',
    ],
    package_dir={'rst-tools':
                 'rst_tools'},
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    entry_points="""
    [console_scripts]
    rst-shift = rst_tools.rst_shift:main
    rst-slideoutline = rst_tools.rst_slideoutline:main
    """,
    keywords='ReStructuredText',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
