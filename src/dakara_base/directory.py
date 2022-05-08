"""Directory helper module.

This module gives application name and project name:

>>> APP_NAME
... "dakara"
>>> PROJECT_NAME
... "DakaraProject"

It also gives an evolved version of `appdirs.AppDirs` that returns `path.Path`
objects:

>>> type(directories.user_config_dir)
... path.Path
"""
from path import Path
from platformdirs import PlatformDirs as AppDirs

APP_NAME = "dakara"
PROJECT_NAME = "DakaraProject"


class AppDirsPath(AppDirs):
    """AppDirs class that returns `path.Path` objects."""

    @property
    def site_config_dir(self):
        return Path(super().site_config_dir)

    @property
    def site_data_dir(self):
        return Path(super().site_data_dir)

    @property
    def user_cache_dir(self):
        return Path(super().user_cache_dir)

    @property
    def user_config_dir(self):
        return Path(super().user_config_dir)

    @property
    def user_data_dir(self):
        return Path(super().user_data_dir)

    @property
    def user_documents_dir(self):
        return Path(super().user_documents_dir)

    @property
    def user_log_dir(self):
        return Path(super().user_log_dir)

    @property
    def user_runtime_dir(self):
        return Path(super().user_runtime_dir)

    @property
    def user_state_dir(self):
        return Path(super().user_state_dir)


directories = AppDirsPath(APP_NAME, PROJECT_NAME, roaming=True)
