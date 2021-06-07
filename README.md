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
