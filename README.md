# Dakara Base

<!-- Badges are displayed for the develop branch -->
[![Travis CI Build Status](https://travis-ci.org/DakaraProject/dakara-base.svg?branch=develop)](https://travis-ci.org/DakaraProject/dakara-base)
[![Appveyor Build status](https://ci.appveyor.com/api/projects/status/50fay6bhsgxispcw/branch/develop?svg=true)](https://ci.appveyor.com/project/neraste/dakara-base/branch/develop)
[![Coverage Status](https://coveralls.io/repos/github/DakaraProject/dakara-base/badge.svg?branch=develop)](https://coveralls.io/github/DakaraProject/dakara-base?branch=develop)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

This project is a collection of tools and helper modules for the Dakara Project.

## Modules available

* `config`: a configuration helper that can load an YAML file and manage loggers;
* `exceptions`: a base class for exceptions;
* `http_client`: an HTTP client dedicated to be used with an API;
* `resources_manager`: a helper for retreiving static files with module-like naming;
* `utils`: other various helpers;
* `websocket_client`: a Websocket client.

## Install

Install the package with:

```sh
python setup.py install
```

## Developpment

### Install dependencies

Please ensure you have a recent enough version of `setuptools`:

```sh
pip install --upgrade "setuptools>=40.0"
```

Install the dependencies with:

```sh
pip install -e ".[tests]"
```

This installs the normal dependencies of the package plus the dependencies for tests.

### Run tests

Run tests simply with:

```sh
python setup.py test
```

To check coverage, use the `coverage` command:

```sh
coverage run setup.py test
coverage report -m
```
