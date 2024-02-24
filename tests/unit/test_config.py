import os
from unittest import TestCase
from unittest.mock import PropertyMock, patch

try:
    from importlib.resources import path

except ImportError:
    from importlib_resources import path

from environs import Env
from path import Path
from yaml.parser import ParserError

from dakara_base.config import (
    AutoEnv,
    Config,
    ConfigInvalidError,
    ConfigNotFoundError,
    ConfigParseError,
    create_config_file,
    create_logger,
    set_loglevel,
)


class AutoEnvTestCase(TestCase):
    """Test the `AutoEnv` class."""

    def test_auto(self):
        """Test to parse some valid types."""
        env = AutoEnv()

        with patch.object(Env, "int") as mocked_int:
            env.auto(int, "aaa")
            mocked_int.assert_called_with("aaa")

        with patch.object(Env, "bool") as mocked_bool:
            env.auto(bool, "aaa")
            mocked_bool.assert_called_with("aaa")

        with patch.object(Env, "float") as mocked_float:
            env.auto(float, "aaa")
            mocked_float.assert_called_with("aaa")

        with patch.object(Env, "list") as mocked_list:
            env.auto(list, "aaa")
            mocked_list.assert_called_with("aaa")

    def test_auto_invalid(self):
        """Test to parse an invalid types."""
        env = AutoEnv()

        with self.assertRaises(AttributeError):
            env.auto(type(None), "aaa")

    def test_get(self):
        """Test to get a value."""
        env = AutoEnv()

        with patch.dict(os.environ, {"PREFIX_AAA": "my_val"}, clear=True):
            with env.prefixed("PREFIX_"):
                self.assertEqual(env.auto(str, "AAA"), "my_val")


class ConfigTestCase(TestCase):
    """Test the `Config` class."""

    def test_return_env_var(self):
        """Test return var env when present."""

        config = Config("dakara")

        # Add value
        config["server"] = "url"

        # Value can be accessed like a regular dict
        self.assertEqual(config.get("server"), "url")
        self.assertEqual(config["server"], "url")

        # Add a environment variable with the same name
        with patch.dict(os.environ, {"DAKARA_SERVER": "url_from_env"}, clear=True):
            # return value from environment variable
            self.assertEqual(config.get("server"), "url_from_env")
            self.assertEqual(config["server"], "url_from_env")

    def test_create_from_dict(self):
        """Test the creation from existing dict."""

        # Create nested dict
        config_raw = {
            "server": {"url": "http://a.b", "token": "gdfgdg"},
            "player": {"config1": "conf", "value": "testvalue"},
        }

        config = Config("DAKARA", config_raw)

        # Check child dicts were also converted
        self.assertIsInstance(config["server"], Config)
        self.assertIsInstance(config["player"], Config)

        # Add a environment variable corresponding to the url param
        with patch.dict(os.environ, {"DAKARA_SERVER_URL": "url_from_env"}, clear=True):
            # return value from environment variable
            self.assertEqual(config.get("server").get("url"), "url_from_env")
            self.assertEqual(config["server"]["url"], "url_from_env")

    def test_cast(self):
        """Test to cast values when getting them."""
        config = Config("DAKARA")

        with patch.dict(
            os.environ,
            {
                "DAKARA_BOOL": "yes",
                "DAKARA_INT": "42",
                "DAKARA_FLOAT": "3.1416",
                "DAKARA_STR": "abcd",
                "DAKARA_LIST": "item1,item2",
            },
            clear=True,
        ):
            self.assertTrue(config.get("bool", False))
            self.assertEqual(config.get("int", 1), 42)
            self.assertAlmostEqual(config.get("float", 1.1), 3.1416)
            self.assertEqual(config.get("str"), "abcd")
            self.assertListEqual(config.get("list", []), ["item1", "item2"])

    def test_set_iterable_reset(self):
        """Test setting an iterable erases previous stored data."""
        config = Config("DAKARA", {"val": True, "spy": True})
        config.set_iterable({"val": False})
        self.assertFalse(config["val"])
        self.assertNotIn("spy", config)

    def test_set_debug(self):
        """Test to set debug mode."""
        config = Config("DAKARA", {"loglevel": "INFO"})
        self.assertNotEqual(config["loglevel"], "DEBUG")
        config.set_debug()
        self.assertEqual(config["loglevel"], "DEBUG")

    @patch.object(Config, "check_mandatory_key")
    def test_check_madatory_keys(self, mocked_check_mandatory_key):
        """Test to check a list of keys."""
        config = Config("DAKARA")
        config.check_mandatory_keys(["key"])

        mocked_check_mandatory_key.assert_called_once_with("key")

    def test_check_madatory_key_missing(self):
        """Test to check config without a required key."""
        config = Config("DAKARA")

        with self.assertRaisesRegex(
            ConfigInvalidError, "Invalid config file, missing 'not-present'"
        ):
            config.check_mandatory_key("not-present")

    def test_load_file_success(self):
        """Test to load a config file."""
        config = Config("DAKARA")

        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG") as logger:
            with path("tests.resources", "config.yaml") as file:
                config.load_file(Path(file))

        # assert the result
        self.assertEqual(config["key"]["subkey"], "value")

        # assert the effect on logs
        self.assertListEqual(
            logger.output,
            ["INFO:dakara_base.config:Loading config file '{}'".format(Path(file))],
        )

    def test_load_file_fail_not_found(self):
        """Test to load a not found config file."""
        config = Config("DAKARA")

        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG"):
            with self.assertRaisesRegex(ConfigNotFoundError, "No config file found"):
                config.load_file(Path("nowhere"))

    @patch("dakara_base.config.yaml.safe_load", autospec=True)
    def test_load_file_fail_parser_error(self, mocked_safe_load):
        """Test to load an invalid config file."""
        # mock the call to yaml
        mocked_safe_load.side_effect = ParserError("parser error")

        config = Config("DAKARA")

        # call the method
        with self.assertLogs("dakara_base.config", "DEBUG"):
            with path("tests.resources", "config.yaml") as file:
                with self.assertRaisesRegex(
                    ConfigParseError, "Unable to parse config file"
                ):
                    config.load_file(Path(file))

    def test_config_env(self):
        """Test to load config and get value from environment."""
        config = Config("DAKARA")

        with self.assertLogs("dakara_base.config", "DEBUG"):
            with path("tests.resources", "config.yaml") as file:
                config.load_file(Path(file))

        self.assertNotEqual(config.get("key").get("subkey"), "myvalue")

        with patch.dict(os.environ, {"DAKARA_KEY_SUBKEY": "myvalue"}, clear=True):
            self.assertEqual(config.get("key").get("subkey"), "myvalue")


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


@patch.object(Path, "copyfile")
@patch.object(Path, "exists")
@patch.object(Path, "mkdir_p")
@patch(
    "dakara_base.directory.AppDirsPath.user_config_dir",
    new_callable=PropertyMock(return_value=Path("path") / "to" / "directory"),
)
@patch(
    "dakara_base.config.path",
)
class CreateConfigFileTestCase(TestCase):
    """Test the config file creator."""

    def test_create_empty(
        self,
        mocked_path,
        mocked_user_config_dir,
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
        mocked_user_config_dir,
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
        mocked_user_config_dir,
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
        mocked_user_config_dir,
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
