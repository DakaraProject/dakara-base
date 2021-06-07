# Dakara Base

<!-- Badges are displayed for the develop branch -->
[![Appveyor Build status](https://ci.appveyor.com/api/projects/status/50fay6bhsgxispcw/branch/develop?svg=true)](https://ci.appveyor.com/project/neraste/dakara-base/branch/develop)
[![Codecov coverage analysis](https://codecov.io/gh/DakaraProject/dakara-base/branch/develop/graph/badge.svg)](https://codecov.io/gh/DakaraProject/dakara-base)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![PyPI version](https://badge.fury.io/py/dakarabase.svg)](https://pypi.python.org/pypi/dakarabase/)
[![PyPI Python versions](https://img.shields.io/pypi/pyversions/dakarabase.svg)](https://pypi.python.org/pypi/dakarabase/)

This project is a collection of tools and helper modules for the Dakara Project.

## Modules available

* `config`: a configuration helper that can load an YAML file and manage loggers;
* `exceptions`: a base class for exceptions;
* `http_client`: an HTTP client dedicated to be used with an API;
* `progress_bar`: a collection of progress bars;
* `safe_workers`: a library to facilitate the manipulation of threads;
* `utils`: other various helpers;
* `websocket_client`: a Websocket client.

## Install

Install the package with:

```sh
pip install dakarabase
```

## Developpment

This package is managed with [Poetry](https://python-poetry.org/):

```sh
pip install poetry
```

### Dependencies

Install the dependencies with:

```sh
poetry install
```

This installs the normal dependencies of the package plus the dependencies for tests.

### Tests

Tests are run by [Pytest](https://docs.pytest.org/en/stable/) and are simply run by:

```sh
poetry run pytest
```

### Imports

Imports are sorted by [isort](https://pycqa.github.io/isort/) with the command:

```sh
poetry run isort .
```

### Code style

The code follows the [PEP8](https://www.python.org/dev/peps/pep-0008/) style guide (88 chars per line).
Quality of code is checked with [Flake8](https://pypi.org/project/flake8/):

```sh
poetry run flake8
```

Style is enforced using [Black](https://github.com/ambv/black):

```sh
poetry run black .
```

You need to call Black before committing changes.
You may want to configure your editor to call it automatically.
Additionnal checking can be manually performed with [Pylint](https://www.pylint.org/).

### Hooks

Pre-commit hooks allow to perform checks before commiting changes.
They are managed with [Pre-commit](https://pre-commit.com/), use the following command to install them:

```sh
poetry run pre-commit install
```
