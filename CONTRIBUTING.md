# Contributing

## Development

### Dependencies

Please ensure you have a recent enough version of `setuptools`:

```sh
pip install --upgrade "setuptools>=46.4.0"
```

Install dependencies with:

```sh
pip install -e ".[dev]"
```

This installs the normal dependencies of the package plus the dependencies for tests.

### Documentation

Documentation is built with [pdoc](https://pdoc.dev/) with the command:

```sh
pdoc --docformat=google -o doc/ ./src/dakara_base
```

### Tests

Tests are run by [Pytest](https://docs.pytest.org/en/stable/) with:

```sh
pytest
```

Both Pytest style and standard Unittest style tests can be used.
Coverage is checked automatically with [Pytest-cov](https://pypi.org/project/pytest-cov/).

### Imports

Imports are sorted by [isort](https://pycqa.github.io/isort/) with the command:

```sh
isort .
```

### Code style

The code follows the [PEP8](https://www.python.org/dev/peps/pep-0008/) style guide (88 characters per line).
Code style is checked with [ruff](https://pypi.org/project/ruff/):

```sh
ruff check .
```

Style is enforced using [Black](https://github.com/ambv/black):

```sh
black .
```

### Hooks

Pre-commit hooks allow to perform checks before commiting changes.
They are managed with [Pre-commit](https://pre-commit.com/), use the following command to install them:

```sh
pre-commit install
```

## Release

This process describes how to release a new version:

1. Move to the `develop` branch and pull.
   ```sh
   git checkout develop
   git pull
   ```
   If there is any cosmetic modification to perform on the changelog file, do it now.
2. Call the bump version script:
   ```sh
   ./bump_version.sh 0.0.0 0.1.0
   ```
   with `0.0.0` the release version and `0.1.0` the next version (without 'v', without '-dev').
3. Push the version commit and its tag:
   ```sh
   git push
   git push origin 0.0.0
   ```
   with the according version number.
4. Move to the `master` branch and merge the created tag into it.
   Then push:
   ```sh
   git checkout master
   git pull
   git merge 0.0.0
   git push
   ```
5. Call the script to create the package:
   ```sh
   ./create_archive.sh
   ```
   The distribution and source distribution are created and published on PyPI.
   Just add your username and password when prompted.
6. On GitHub, draft a new release, set the version number with the created tag ("Existing tag" should read).
   Set the release title with "Version 0.0.0" (with number, you get it?).
   Copy-paste corresponding section of the changelog file in the release description.
   You can now publish the release.
