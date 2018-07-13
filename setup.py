#!/usr/bin/env python

from setuptools import setup, find_packages


setup(name="pynetdicom2",
      packages=find_packages(),
      include_package_data=True,
      version="0.9.0",
      zip_safe=False,  # want users to be able to see included examples,tests
      description="Pure python implementation of the DICOM network protocol",
      author="Pavel 'Blane' Tuchin",
      author_email="blane.public@gmail.com",
      url="https://github.com/blanebf/pynetdicom2",
      license="LICENCE.txt",
      keywords="dicom python medicalimaging",
      classifiers=["License :: OSI Approved :: MIT License",
                   "Intended Audience :: Developers",
                   "Intended Audience :: Healthcare Industry",
                   "Intended Audience :: Science/Research",
                   "Development Status :: 4 - Beta",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 2.7",
                   "Operating System :: OS Independent",
                   "Topic :: Scientific/Engineering :: Medical Science Apps.",
                   "Topic :: Scientific/Engineering :: Physics",
                   "Topic :: Software Development :: Libraries"],
      long_description=open('README.rst').read(),
      install_requires=["six", "pydicom >= 0.9.7"])
