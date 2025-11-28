#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='pyfacturx',
    version='1.0.1',
    author='',
    author_email='',
    url='',
    description='Factur-X: electronic invoicing standard for France',
    long_description=open('README.md').read(),
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
        "Operating System :: OS Independent",
    ],
    keywords='e-invoice Factur-X AIFE',
    packages=find_packages(),
    install_requires=[r.strip() for r in
                      open('requirements.txt').read().splitlines()],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'facturx = bin.cli:main', ],
    },
)
