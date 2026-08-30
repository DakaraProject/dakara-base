"""Directory helper module.

This module gives application name and project name:

>>> APP_NAME
... "dakara"
>>> PROJECT_NAME
... "DakaraProject"

It also gives a preconfigured `platformdirs.PlatformDirs` for Dakara.
"""

from platformdirs import PlatformDirs

APP_NAME = "dakara"
"""Lower-case short name of the project."""

PROJECT_NAME = "DakaraProject"
"""Pascal-case long name of the project."""


directories = PlatformDirs(APP_NAME, PROJECT_NAME, roaming=True)
