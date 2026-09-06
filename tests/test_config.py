import logging
from importlib.resources import as_file, files
from pathlib import Path

import pytest
from platformdirs import PlatformDirs
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


class TestAutoEnv:
    def test_auto(self, monkeypatch):
        """Test to parse some valid types."""
        env = AutoEnv()

        monkeypatch.setenv("INTEGER", "39")
        assert env.auto(int, "INTEGER") == 39

        monkeypatch.setenv("BOOLEAN_INT_TRUE", "1")
        assert env.auto(bool, "BOOLEAN_INT_TRUE")

        monkeypatch.setenv("BOOLEAN_INT_FALSE", "0")
        assert not env.auto(bool, "BOOLEAN_INT_FALSE")

        monkeypatch.setenv("BOOLEAN_WORD_TRUE", "true")
        assert env.auto(bool, "BOOLEAN_WORD_TRUE")

        monkeypatch.setenv("BOOLEAN_WORD_FALSE", "false")
        assert not env.auto(bool, "BOOLEAN_WORD_FALSE")

        monkeypatch.setenv("FLOAT", "0.1")
        assert env.auto(float, "FLOAT") == 0.1

        monkeypatch.setenv("LIST", "leek,mikan,banana,thuna")
        assert env.auto(list, "LIST") == ["leek", "mikan", "banana", "thuna"]

    def test_auto_invalid(self):
        """Test to parse an invalid types."""
        env = AutoEnv()

        with pytest.raises(AttributeError):
            env.auto(type(None), "UNKNOWN")

    def test_get(self, monkeypatch):
        """Test to get a value."""
        env = AutoEnv()

        monkeypatch.setenv("PREFIX_STR", "my val")
        with env.prefixed("PREFIX_"):
            assert env.auto(str, "STR") == "my val"


class TestConfig:
    def test_return_env_var(self, monkeypatch):
        """Test return var env when present."""

        config = Config("dakara")

        # Add value
        config["server"] = "url"

        # Value can be accessed like a regular dict
        assert config.get("server") == "url"
        assert config["server"] == "url"

        # Add a environment variable with the same name
        monkeypatch.setenv("DAKARA_SERVER", "url_from_env")
        assert config.get("server") == "url_from_env"
        assert config["server"] == "url_from_env"

    def test_create_from_dict(self, monkeypatch):
        """Test the creation from existing dict."""

        # Create nested dict
        config_raw = {
            "server": {"url": "http://a.b", "token": "gdfgdg"},
            "player": {"config1": "conf", "value": "testvalue"},
        }

        config = Config("DAKARA", config_raw)

        # Check child dicts were also converted
        assert isinstance(config["server"], Config)
        assert isinstance(config["player"], Config)

        # Add a environment variable corresponding to the url param
        monkeypatch.setenv("DAKARA_SERVER_URL", "url_from_env")
        assert config.get("server").get("url") == "url_from_env"
        assert config["server"]["url"] == "url_from_env"

    def test_cast(self, monkeypatch):
        """Test to cast values when getting them."""
        config = Config("DAKARA")

        monkeypatch.setenv("DAKARA_BOOL", "yes")
        monkeypatch.setenv("DAKARA_INT", "42")
        monkeypatch.setenv("DAKARA_FLOAT", "3.1416")
        monkeypatch.setenv("DAKARA_STR", "abcd")
        monkeypatch.setenv("DAKARA_LIST", "item1,item2")
        assert config.get("bool", False)
        assert config.get("int", 1) == 42
        assert config.get("float", 1.1) == pytest.approx(3.1416)
        assert config.get("str") == "abcd"
        assert config.get("list", []) == ["item1", "item2"]

    def test_set_iterable_reset(self):
        """Test setting an iterable erases previous stored data."""
        config = Config("DAKARA", {"val": True, "spy": True})
        config.set_iterable({"val": False})

        assert not config["val"]
        assert "spy" not in config

    def test_set_debug(self):
        """Test to set debug mode."""
        config = Config("DAKARA", {"loglevel": "INFO"})
        assert config["loglevel"] != "DEBUG"

        config.set_debug()
        assert config["loglevel"] == "DEBUG"

    def test_check_madatory_keys(self):
        """Test to check a list of keys."""
        config = Config("DAKARA", {"key": "value"})
        config.check_mandatory_keys(["key"])

    def test_check_madatory_key_missing(self):
        """Test to check config without a required key."""
        config = Config("DAKARA")

        with pytest.raises(
            ConfigInvalidError, match="Invalid config file, missing 'not-present'"
        ):
            config.check_mandatory_key("not-present")

    def test_load_file_success(self, caplog):
        """Test to load a config file."""
        config = Config("DAKARA")

        # call the method
        caplog.set_level(logging.DEBUG)
        with as_file(files("tests.resources").joinpath("config.yaml")) as file:
            config.load_file(file.name, directory=file.parent)

        # assert the result
        assert config["key"]["subkey"] == "value"

        # assert the effect on logs
        assert caplog.record_tuples == [
            ("dakara_base.config", logging.INFO, f"Loading config file '{Path(file)}'")
        ]

    def test_load_file_success_no_directory(self, caplog, mocker):
        """Test to load a config file without specifying a directory."""
        mocker.patch.object(
            PlatformDirs,
            "user_config_dir",
            new_callable=mocker.PropertyMock(return_value=Path("path/to/directory")),
        ),
        mocker.patch.object(
            Path, "read_text", return_value="{key: value}", autospec=True
        )
        config = Config("DAKARA")

        # call the method
        caplog.set_level(logging.DEBUG)
        config.load_file("config.yaml")

        # assert the result
        assert config["key"] == "value"

        # assert the effect on logs
        assert caplog.record_tuples == [
            (
                "dakara_base.config",
                logging.INFO,
                f"Loading config file '{Path('path/to/directory/config.yaml')}'",
            )
        ]

    def test_load_file_fail_not_found(self):
        """Test to load a not found config file."""
        config = Config("DAKARA")

        # call the method
        with pytest.raises(ConfigNotFoundError, match="No config file found"):
            config.load_file("nowhere", directory=Path("/"))

    def test_load_file_fail_parser_error(self, mocker):
        """Test to load an invalid config file."""
        # mock the call to yaml
        mocker.patch(
            "dakara_base.config.yaml.safe_load",
            autospec=True,
            side_effect=ParserError("parser error"),
        )

        config = Config("DAKARA")

        # call the method
        with as_file(files("tests.resources").joinpath("config.yaml")) as file:
            with pytest.raises(ConfigParseError, match="Unable to parse config file"):
                config.load_file(file.name, directory=file.parent)

    def test_config_env(self, monkeypatch):
        """Test to load config and get value from environment."""
        config = Config("DAKARA")

        with as_file(files("tests.resources").joinpath("config.yaml")) as file:
            config.load_file(file.name, directory=file.parent)

        assert config.get("key").get("subkey") != "myvalue"

        monkeypatch.setenv("DAKARA_KEY_SUBKEY", "myvalue")
        assert config.get("key").get("subkey") == "myvalue"


@pytest.fixture
def test_create_logger_mockers(mocker):
    return (
        mocker.patch("dakara_base.config.LOG_FORMAT", "my format"),
        mocker.patch("dakara_base.config.LOG_LEVEL", "my level"),
        mocker.patch(
            "dakara_base.config.progressbar.streams.wrap_stderr", autospec=True
        ),
        mocker.patch("dakara_base.config.coloredlogs.install", autospec=True),
    )


class TestCreateLogger:
    def test_normal(self, test_create_logger_mockers):
        """Test to call the method normally."""
        _, _, mocked_wrap_stderr, mocked_install = test_create_logger_mockers

        # call the method
        create_logger()

        # assert the call
        mocked_install.assert_called_with(fmt="my format", level="my level")
        mocked_wrap_stderr.assert_not_called()

    def test_wrap(self, test_create_logger_mockers):
        """Test to call the method and request to wrap stderr."""
        _, _, mocked_wrap_stderr, mocked_install = test_create_logger_mockers

        # call the method
        create_logger(wrap=True)

        # assert the call
        mocked_install.assert_called_with(fmt="my format", level="my level")
        mocked_wrap_stderr.assert_called_with()

    def test_custom(self, test_create_logger_mockers):
        """Test to call the method with custom format and level."""
        _, _, mocked_wrap_stderr, mocked_install = test_create_logger_mockers

        # call the method
        create_logger(
            custom_log_format="my custom format", custom_log_level="my custom level"
        )

        # assert the call
        mocked_install.assert_called_with(
            fmt="my custom format", level="my custom level"
        )
        mocked_wrap_stderr.assert_not_called()


class TestSetLogLevel:
    def test_configure_logger(self, mocker):
        """Test to configure the logger."""
        mocked_set_level = mocker.patch(
            "dakara_base.config.coloredlogs.set_level", autospec=True
        )

        # call the method
        set_loglevel({"loglevel": "DEBUG"})

        # assert the result
        mocked_set_level.assert_called_with("DEBUG")

    def test_configure_logger_no_level(self, mocker):
        """Test to configure the logger with no log level."""
        mocked_set_level = mocker.patch(
            "dakara_base.config.coloredlogs.set_level", autospec=True
        )

        # call the method
        set_loglevel({})

        # assert the result
        mocked_set_level.assert_called_with("INFO")


@pytest.fixture
def test_create_config_file_mockers(mocker):
    return (
        mocker.patch("dakara_base.config.copyfile", autospec=True),
        mocker.patch.object(Path, "exists", autospec=True),
        mocker.patch.object(Path, "mkdir", autospec=True),
        mocker.patch.object(
            PlatformDirs,
            "user_config_dir",
            new_callable=mocker.PropertyMock(return_value=Path("path/to/directory")),
        ),
        mocker.patch(
            "dakara_base.config.as_file",
            autospec=True,
        ),
        mocker.patch("dakara_base.config.files", autospec=True),
        mocker.patch("dakara_base.config.input"),
    )


class TestCreateConfigFile:
    def test_create_empty(self, test_create_config_file_mockers, caplog):
        """Test create the config file in an empty directory."""
        # setup mocks
        (
            mocked_copyfile,
            mocked_exists,
            mocked_mkdir,
            mocked_user_config_dir,
            mocked_as_file,
            mocked_files,
            mocked_input,
        ) = test_create_config_file_mockers
        mocked_exists.return_value = False
        mocked_as_file.return_value.__enter__.return_value = Path("path/to/source")

        caplog.set_level(logging.INFO)

        # call the function
        create_config_file("module.resources", "config.yaml")

        # assert the call
        mocked_files.assert_called_with("module.resources")
        mocked_files.return_value.joinpath.assert_called_with("config.yaml")
        mocked_mkdir.assert_called_with(
            Path("path/to/directory"), parents=True, exist_ok=True
        )
        mocked_exists.assert_called_with(Path("path/to/directory/config.yaml"))
        mocked_copyfile.assert_called_with(
            Path("path/to/source"),
            Path("path/to/directory/config.yaml"),
        )

        # assert the logs
        assert caplog.record_tuples == [
            (
                "dakara_base.config",
                logging.INFO,
                f"Config created in '{Path('path/to/directory/config.yaml')}'",
            )
        ]

    def test_create_existing_no(self, test_create_config_file_mockers):
        """Test create the config file in a non empty directory."""
        # setup mocks
        (
            mocked_copyfile,
            mocked_exists,
            mocked_mkdir,
            mocked_user_config_dir,
            mocked_as_file,
            mocked_files,
            mocked_input,
        ) = test_create_config_file_mockers
        mocked_exists.return_value = True
        mocked_input.return_value = "no"
        mocked_as_file.return_value.__enter__.return_value = Path("path/to/source")

        # call the function
        create_config_file("module.resources", "config.yaml")

        # assert the call
        mocked_copyfile.assert_not_called()
        mocked_input.assert_called_with(
            "{} already exists, overwrite? [y/N] ".format(
                Path("path/to/directory/config.yaml")
            )
        )

    def test_create_existing_force(self, test_create_config_file_mockers):
        """Test create the config file in a non empty directory with force overwrite."""
        # setup mocks
        (
            mocked_copyfile,
            mocked_exists,
            mocked_mkdir,
            mocked_user_config_dir,
            mocked_as_file,
            mocked_files,
            mocked_input,
        ) = test_create_config_file_mockers
        mocked_as_file.return_value.__enter__.return_value = Path("path/to/source")

        # call the function
        create_config_file("module.resources", "config.yaml", force=True)

        # assert the call
        mocked_exists.assert_not_called()
        mocked_input.assert_not_called()
        mocked_copyfile.assert_called_with(
            Path("path/to/source"),
            Path("path/to/directory/config.yaml"),
        )

    def test_create_custom_directory(self, test_create_config_file_mockers, caplog):
        """Test create the config file in an empty directory."""
        # setup mocks
        (
            mocked_copyfile,
            mocked_exists,
            mocked_mkdir,
            mocked_user_config_dir,
            mocked_as_file,
            mocked_files,
            mocked_input,
        ) = test_create_config_file_mockers
        mocked_exists.return_value = False
        mocked_as_file.return_value.__enter__.return_value = Path("path/to/source")

        caplog.set_level(logging.INFO)

        # call the function
        create_config_file(
            "module.resources", "config.yaml", directory=Path("custom/path")
        )

        # assert the call
        mocked_mkdir.assert_called_with(
            Path("custom/path"), parents=True, exist_ok=True
        )

        # assert the logs
        assert caplog.record_tuples == [
            (
                "dakara_base.config",
                logging.INFO,
                f"Config created in '{Path('custom/path/config.yaml')}'",
            )
        ]
