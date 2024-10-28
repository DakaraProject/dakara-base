import logging
from unittest import TestCase

from dakara_base.version_check import check_version


class CheckVersionTestCase(TestCase):
    """Test the version checker."""

    def test_check_version_release(self):
        """Test to display the version for a release."""
        with self.assertLogs("dakara_base.version_check", "DEBUG") as logger:
            check_version("my project", "0.0.0", "1970-01-01")

        # assert effect on logs
        self.assertListEqual(
            logger.output,
            ["INFO:dakara_base.version_check:Dakara my project 0.0.0 (1970-01-01)"],
        )

    def test_check_version_release_logger(self):
        """Test to display the version for a release using a custom logger."""
        local_logger = logging.getLogger("my_logger")

        with self.assertLogs("my_logger", "DEBUG") as logger:
            check_version("my project", "0.0.0", "1970-01-01", local_logger)

        # assert effect on logs
        self.assertListEqual(
            logger.output,
            ["INFO:my_logger:Dakara my project 0.0.0 (1970-01-01)"],
        )

    def test_check_version_non_release(self):
        """Test to display the version for a non release."""
        with self.assertLogs("dakara_base.version_check", "DEBUG") as logger:
            check_version("my project", "0.1.0-dev", "1970-01-01")

        # assert effect on logs
        self.assertListEqual(
            logger.output,
            [
                "INFO:dakara_base.version_check:Dakara my project 0.1.0-dev "
                "(1970-01-01)",
                "WARNING:dakara_base.version_check:"
                "You are running a dev version, use it at your own risks!",
            ],
        )
