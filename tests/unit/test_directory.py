from unittest import TestCase

from path import Path

from dakara_base.directory import AppDirsPath


class AppDirsPathTestCase(TestCase):
    def test_properties(self):
        appdirs = AppDirsPath("appname", "authorname")

        self.assertIsInstance(appdirs.site_config_dir, Path)
        self.assertIsInstance(appdirs.site_data_dir, Path)
        self.assertIsInstance(appdirs.user_cache_dir, Path)
        self.assertIsInstance(appdirs.user_config_dir, Path)
        self.assertIsInstance(appdirs.user_data_dir, Path)
        self.assertIsInstance(appdirs.user_log_dir, Path)
        self.assertIsInstance(appdirs.user_state_dir, Path)
