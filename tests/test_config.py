from unittest import TestCase
from unittest.mock import patch

try:
    from importlib.resources import path

except ImportError:
    from importlib_resources import path

from path import Path
from yaml.parser import ParserError

from dakara_base.config import (
    ConfigInvalidError,
    ConfigNotFoundError,
    ConfigParseError,
    create_config_file,
    create_logger,
    get_config_directory,
    get_config_file,
    load_config,
    set_loglevel,
)


class LoadConfigTestCase(TestCase):
    """Test the `load_config` function."""

    def test_success(self):
        """Test to load a config file."""
        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG") as logger:
            with path("tests.resources", "config.yaml") as file:
                config = load_config(Path(file), False)

        # assert the result
        self.assertDictEqual(config, {"key": {"subkey": "value"}})

        # assert the effect on logs
        self.assertListEqual(
            logger.output,
            ["INFO:dakara_base.config:Loading config file '{}'".format(Path(file))],
        )

    def test_success_debug(self):
        """Test to load the config file with debug mode enabled."""
        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG"):
            with path("tests.resources", "config.yaml") as file:
                config = load_config(Path(file), True)

        # assert the result
        self.assertDictEqual(config, {"key": {"subkey": "value"}, "loglevel": "DEBUG"})

    def test_fail_not_found(self):
        """Test to load a not found config file."""
        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG"):
            with self.assertRaisesRegex(ConfigNotFoundError, "No config file found"):
                load_config(Path("nowhere"), False)

    @patch("dakara_base.config.yaml.load", autospec=True)
    def test_load_config_fail_parser_error(self, mocked_load):
        """Test to load an invalid config file."""
        # mock the call to yaml
        mocked_load.side_effect = ParserError("parser error")

        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG"):
            with path("tests.resources", "config.yaml") as file:
                with self.assertRaisesRegex(
                    ConfigParseError, "Unable to parse config file"
                ):
                    load_config(Path(file), False)

    def test_load_config_fail_missing_keys(self):
        """Test to load a config file without required keys."""
        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG"):
            with path("tests.resources", "config.yaml") as file:
                with self.assertRaisesRegex(
                    ConfigInvalidError, "Invalid config file, missing 'not-present'"
                ):
                    load_config(Path(file), False, ["not-present"])


@patch("dakara_base.config.LOG_FORMAT", "my format")
@patch("dakara_base.config.LOG_LEVEL", "my level")
class CreateLoggerTestCase(TestCase):
    """Test the `create_logger` function."""

    @patch("dakara_base.progress_bar.progressbar.streams.wrap_stderr")
    @patch("dakara_base.config.coloredlogs.install", autospec=True)
    def test_normal(self, mocked_install, mocked_wrap_stderr):
        """Test to call the method normally."""
        # call the method
        create_logger()

        # assert the call
        mocked_install.assert_called_with(fmt="my format", level="my level")
        mocked_wrap_stderr.assert_not_called()

    @patch("dakara_base.progress_bar.progressbar.streams.wrap_stderr")
    @patch("dakara_base.config.coloredlogs.install", autospec=True)
    def test_wrap(self, mocked_install, mocked_wrap_stderr):
        """Test to call the method and request to wrap stderr."""
        # call the method
        create_logger(wrap=True)

        # assert the call
        mocked_install.assert_called_with(fmt="my format", level="my level")
        mocked_wrap_stderr.assert_called_with()

    @patch("dakara_base.progress_bar.progressbar.streams.wrap_stderr")
    @patch("dakara_base.config.coloredlogs.install", autospec=True)
    def test_custom(self, mocked_install, mocked_wrap_stderr):
        """Test to call the method with custom format and level."""
        # call the method
        create_logger(
            custom_log_format="my custom format", custom_log_level="my custom level"
        )

        # assert the call
        mocked_install.assert_called_with(
            fmt="my custom format", level="my custom level"
        )
        mocked_wrap_stderr.assert_not_called()


class SetLoglevelTestCase(TestCase):
    """Test the `set_loglevel` function."""

    @patch("dakara_base.config.coloredlogs.set_level", autospec=True)
    def test_configure_logger(self, mocked_set_level):
        """Test to configure the logger."""
        # call the method
        set_loglevel({"loglevel": "DEBUG"})

        # assert the result
        mocked_set_level.assert_called_with("DEBUG")

    @patch("dakara_base.config.coloredlogs.set_level", autospec=True)
    def test_configure_logger_no_level(self, mocked_set_level):
        """Test to configure the logger with no log level."""
        # call the method
        set_loglevel({})

        # assert the result
        mocked_set_level.assert_called_with("INFO")


class GetConfigDirectoryTestCase(TestCase):
    """Test the config directory getter."""

    @patch("sys.platform", "linux")
    def test_linux(self):
        """Test to get config directory for Linux."""
        directory = get_config_directory()

        self.assertEqual(directory, Path("~") / ".config" / "dakara")

    @patch("sys.platform", "win32")
    def test_windows(self):
        """Test to get config directory for Windows."""
        directory = get_config_directory()

        self.assertEqual(directory, Path("$APPDATA") / "Dakara")

    @patch("sys.platform", "unknown")
    def test_unknown(self):
        """Test to get config directory for unknown OS."""
        with self.assertRaisesRegex(
            NotImplementedError,
            r"This operating system \(unknown\) is not currently supported",
        ):
            get_config_directory()


@patch.object(Path, "copyfile")
@patch.object(Path, "exists")
@patch.object(Path, "mkdir_p")
@patch(
    "dakara_base.config.get_config_file",
    return_value=Path("path") / "to" / "directory" / "config.yaml",
)
@patch(
    "dakara_base.config.path",
)
class CreateConfigFileTestCase(TestCase):
    """Test the config file creator."""

    def test_create_empty(
        self,
        mocked_path,
        mocked_get_config_file,
        mocked_mkdir_p,
        mocked_exists,
        mocked_copyfile,
    ):
        """Test create the config file in an empty directory."""
        # setup mocks
        mocked_exists.return_value = False

        # call the function
        with self.assertLogs("dakara_base.config") as logger:
            create_config_file("module.resources", "config.yaml")

        # assert the call
        mocked_path.assert_called_with("module.resources", "config.yaml")
        mocked_get_config_file.assert_called_with("config.yaml")
        mocked_mkdir_p.assert_called_with()
        mocked_exists.assert_called_with()
        mocked_copyfile.assert_called_with(
            Path("path") / "to" / "directory" / "config.yaml"
        )

        # assert the logs
        self.assertListEqual(
            logger.output,
            [
                "INFO:dakara_base.config:Config created in '{}'".format(
                    Path("path") / "to" / "directory" / "config.yaml"
                )
            ],
        )

    @patch("dakara_base.config.input")
    def test_create_existing_no(
        self,
        mocked_input,
        mocked_path,
        mocked_get_config_file,
        mocked_mkdir_p,
        mocked_exists,
        mocked_copyfile,
    ):
        """Test create the config file in a non empty directory."""
        # setup mocks
        mocked_exists.return_value = True
        mocked_input.return_value = "no"

        # call the function
        create_config_file("module.resources", "config.yaml")

        # assert the call
        mocked_copyfile.assert_not_called()
        mocked_input.assert_called_with(
            "{} already exists, overwrite? [y/N] ".format(
                Path("path") / "to" / "directory" / "config.yaml"
            )
        )

    @patch("dakara_base.config.input")
    def test_create_existing_invalid_input(
        self,
        mocked_input,
        mocked_path,
        mocked_get_config_file,
        mocked_mkdir_p,
        mocked_exists,
        mocked_copyfile,
    ):
        """Test create the config file in a non empty directory with invalid input."""
        # setup mocks
        mocked_exists.return_value = True
        mocked_input.return_value = ""

        # call the function
        create_config_file("module.resources", "config.yaml")

        # assert the call
        mocked_copyfile.assert_not_called()

    @patch("dakara_base.config.input")
    def test_create_existing_force(
        self,
        mocked_input,
        mocked_path,
        mocked_get_config_file,
        mocked_mkdir_p,
        mocked_exists,
        mocked_copyfile,
    ):
        """Test create the config file in a non empty directory with force overwrite."""
        # call the function
        create_config_file("module.resources", "config.yaml", force=True)

        # assert the call
        mocked_exists.assert_not_called()
        mocked_input.assert_not_called()
        mocked_copyfile.assert_called_with(
            Path("path") / "to" / "directory" / "config.yaml"
        )


@patch(
    "dakara_base.config.get_config_directory",
    return_value=Path("path") / "to" / "directory",
)
class GetConfigFileTestCase(TestCase):
    """Test the config file getter."""

    def test_get(self, mocked_get_config_directory):
        """Test to get config file."""
        result = get_config_file("config.yaml")
        self.assertEqual(result, Path("path") / "to" / "directory" / "config.yaml")
