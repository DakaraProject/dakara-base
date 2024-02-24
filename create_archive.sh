#!/bin/bash

# strict mode
set -eu

# getting version of the package
version=$(python -c "from setuptools import setup; setup" --version)
echo "Creating archive for dakara_base v$version"

# install twine
pip install --upgrade twine build

# clean the dist directory
rm -rf dist/*

# create the distribution packages
python -m build

# upload to PyPI
echo "Package will be uploaded tp Pypi"
python -m twine upload dist/*
