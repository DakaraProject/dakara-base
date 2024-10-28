# Dakara Base

<!-- Badges are displayed for the develop branch -->
[![PyPI version](https://badge.fury.io/py/dakarabase.svg)](https://pypi.python.org/pypi/dakarabase/)
[![PyPI Python versions](https://img.shields.io/pypi/pyversions/dakarabase.svg)](https://pypi.python.org/pypi/dakarabase/)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/dakarabase/)
[![Tests status](https://github.com/DakaraProject/dakara-base/actions/workflows/ci.yml/badge.svg)](https://github.com/DakaraProject/dakara-base/actions/workflows/ci.yml)
[![Code coverage status](https://codecov.io/gh/DakaraProject/dakara-base/branch/develop/graph/badge.svg)](https://codecov.io/gh/DakaraProject/dakara-base)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

This project is a collection of tools and helper modules for the Dakara Project.

## Modules available

- `config`: a helper that manages config and loggers;
- `directory`: a helper to manage application directories;
- `exceptions`: a base class for exceptions and exception handlers;
- `http_client`: an HTTP client dedicated to be used with an API;
- `progress_bar`: a collection of progress bars;
- `safe_workers`: a library to facilitate the manipulation of threads;
- `utils`: other various helpers;
- `version_check`: a checker for the version of a project;
- `websocket_client`: a Websocket client.

## Install

Install the package with:

```sh
pip install dakarabase
```

If you have downloaded the repo, you can install the package directly with:

```sh
pip install .
```

## Development

Please read the [developers documentation](CONTRIBUTING.md).
