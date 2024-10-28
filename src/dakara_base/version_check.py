"""
Version checker module.

This module provides the `check_version` function that displays the current
version and checks if it is not a prerelease.
"""

import logging

from packaging.version import parse

logger_default = logging.getLogger(__name__)


def check_version(project, version, date, logger=None):
    """Display version number and check if on release.

    Args:
        project (str): Name of the project (without "Dakara" prefix).
        version (str): Version of the project.
        date (str): Date of the version.
        logger (logging.logger): Logger to use, default to this file's logger.
    """
    if logger is None:
        logger = logger_default

    # log version
    logger.info("Dakara %s %s (%s)", project, version, date)

    # check version is a release
    version_parsed = parse(version)
    if version_parsed.is_prerelease:
        logger.warning("You are running a dev version, use it at your own risks!")
