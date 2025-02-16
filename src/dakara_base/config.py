"""Config helper module.

This module gives the class `Config` that handles the config. It can load
values from a YAML file and from environment variables:

>>> from pathlib import Path
>>> config = Config("DAKARA")
>>> config.load_file(Path("path/to/file.yaml"))
>>> config.set_debug()
>>> config.check_mandatory_key("server")
>>> config.get("server").get("address")

The module has two functions to configure loggers: `create_logger`, which
installs the logger using coloredlogs, and `set_loglevel`, which sets the
loglevel of the logger according to the config. Usually, you call the first one
before reading the config, as `load_config` needs a logger, then call the
latter one:

>>> create_logger()
>>> from pathlib import Path
>>> config = Config("DAKARA")
>>> config.load_file(Path("path/to/file.yaml"))
>>> set_loglevel(config)

If you use progress bar and logging at the same time, you should call
`create_logger` with `wrap=True`.

The module has one function to manage Dakara Project config files,
`create_config_file`, that copies a given config file stored in module resources to
the configuration directory:

>>> create_config_file("module.resources", "my_config.yaml")
"""

import logging
from collections import UserDict
from importlib.resources import as_file, files
from shutil import copyfile

import coloredlogs
import progressbar
import yaml
import yaml.parser
from environs import Env, EnvError

from dakara_base.directory import directories
from dakara_base.exceptions import DakaraError
from dakara_base.utils import strtobool

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"
LOG_LEVEL = "INFO"

logger = logging.getLogger(__name__)


class AutoEnv(Env):
    """Environment variable reader with an automatic method."""

    def auto(self, type, *args, **kwargs):
        type_str = type.__name__
        return getattr(self, type_str)(*args, **kwargs)


class Config(UserDict):
    """Configuration object.

    This object behaves similarly to a dictionary. Its values can be populated
    from a file at first. Then, when accessing a value with a key, it first
    checks if a value with similar name exists as an environment variable. In
    that case, the environment variable is given, otherwise the stored value is
    given.

    Values can be loaded from a file, previous values stored in the config
    would be discarded.

    >>> from pathlib import Path
    >>> conf = Config("prefix")
    >>> conf.load_file(Path("config.yaml"))

    When checking environment variables, the looked up variable name is
    prefixed and made upper-case.

    >>> conf = Config("prefix", {"key1": "foo", "key2": "bar"})
    >>> conf
    {"key1": "foo", "key2": "bar"}
    >>> conf.get("key1")
    "foo"
    >>> # let's say PREFIX_KEY2 is an environment variable with value "spam"
    >>> conf.get("key2")
    "spam"

    Values of nested `Config` objects will have accumulated prefixes
    (separated by an underscore):

    >>> conf = Config("prefix", {"sub": {"key": "foo"}})
    >>> # let's say PREFIX_SUB_KEY is an environment variable with value "bar"
    >>> cong.get("sub").get("key")
    "bar"

    By default, the value obtained from the environment is a string. If a
    default value is provided to `get`, the returned value from the environment
    will be parsed to the type of that default value:

    >>> conf = Config("prefix", {"key": 42})
    >>> # let's say PREFIX_KEY is an environment variable with value "39"
    >>> conf.get("key")
    "39"
    >>> cong.get("key", 0)
    39

    You can check `environs.Env` for the supported types. Note stored values
    are parsed from the config file by the YAML library.

    Attributes:
        prefix (str): Prefix to use when looking for value in environment
            variables.
        env (AutoEnv): Environment parser.

    Args:
        prefix (str): Prefix to use when looking for value in environment
            variables.
        iterable (iterable): Values to store.
    """

    def __init__(self, prefix, iterable=None):
        super().__init__()

        self.prefix = prefix
        self.env = AutoEnv()

        # create values in object if any provided
        if iterable:
            self.set_iterable(iterable)

    def set_iterable(self, iterable):
        """Set config values from the provided iterable.

        Dictionaries will be converted into Config with a sub-prefix.

        Args:
            iterable (dict): Dictionary of values.
        """
        # recursively convert dictionaries into Config objects
        iterable = {
            key: (
                self.__class__("{}_{}".format(self.prefix, key), val)
                if isinstance(val, dict)
                else val
            )
            for key, val in iterable.items()
        }

        # reset config data with values from the iterable
        self.data.clear()
        self.data.update(iterable)

    def set_debug(self, debug=True):
        """Set log level of the config to debug.

        Args:
            debug (bool): If `True` (default), set log level to "DEBUG".
        """
        if debug:
            self.data["loglevel"] = "DEBUG"

    def check_mandatory_keys(self, keys):
        """Check if a list of keys is present in the config.

        Args:
            keys (list of str): Keys that must be present in the config.
        """
        for key in keys:
            self.check_mandatory_key(key)

    def check_mandatory_key(self, key):
        """Check if a key is present in the config.

        Args:
            keys (str): Key that must be present in the config.

        Raises:
            ConfigInvalidError: If the config misses a critical section.
        """
        if key not in self.data:
            raise ConfigInvalidError("Invalid config file, missing '{}'".format(key))

    def load_file(self, config_path):
        """Load config from a given YAML file.

        Args:
            config_path (pathlib.Path): Path to the config file.

        Raises:
            ConfigNotFoundError: If the config file cannot be open.
            ConfigParseError: If the config cannot be parsed.
        """
        logger.info("Loading config file '%s'", config_path)

        # load and parse the file and create config data
        try:
            with config_path.open() as file:
                self.set_iterable(yaml.safe_load(file))

        except yaml.parser.ParserError as error:
            raise ConfigParseError("Unable to parse config file") from error

        except FileNotFoundError as error:
            raise ConfigNotFoundError("No config file found") from error

    def get_value_from_env(self, key, type=None):
        """Get the value from prefixed upper case environment variable.

        Args:
            key (str): Name of the variable without prefix.
            type (type): Type of the variable. If not provided, default to
                string.

        Returns:
            str: Value from environment variable.
        """
        with self.env.prefixed("{}_".format(self.prefix.upper())):
            # use type if provided
            if type:
                return self.env.auto(type, key.upper())

            # fallback to default behavior
            return self.env(key.upper())

    def __getitem__(self, key):
        # try to get value from environment
        try:
            return self.get_value_from_env(key)

        except EnvError:
            return super().__getitem__(key)

    def get(self, key, default=None):
        """Return the value for the provided key.

        If a default value is provided, it will determine the type of the
        returned value when getting it from the environment variables.

        Args:
            key (any): Key to retreive.
            default (any): Default value if the key cannot be found.

        Returns:
            any: Value. If `default` was provided, it will be of the same type.
        """
        # guess cast from default value
        cast = None
        if default is not None:
            cast = type(default)

        # get value from environment, then from dict
        try:
            return self.get_value_from_env(key, cast)

        except EnvError:
            return super().get(key, default)


def create_logger(wrap=False, custom_log_format=None, custom_log_level=None):
    """Create logger.

    Args:
        wrap (bool): If True, wrap the standard error stream for using logging
            and progress bar. You have to enable this flag if you use
            `progress_bar`.
        custom_log_format (str): Custom format string to use for logs.
        custom_log_level (str): Custom level of logging.
    """
    # wrap stderr on demand
    if wrap:
        progressbar.streams.wrap_stderr()

    # setup loggers
    log_format = custom_log_format or LOG_FORMAT
    log_level = custom_log_level or LOG_LEVEL
    coloredlogs.install(fmt=log_format, level=log_level)


def set_loglevel(config):
    """Set logger level.

    Arguments:
        config (Config): Dictionary of the config.
    """
    loglevel = config.get("loglevel", LOG_LEVEL)
    coloredlogs.set_level(loglevel)


def create_config_file(resource, filename, force=False):
    """Create a new config file in user directory.

    Args:
        resource (str): Resource where to find the config file.
        filename (str): Name of the config file.
        force (bool): If True, config file in user directory is overwritten if
            it existed already. Otherwise, prompt the user.
    """
    with as_file(files(resource).joinpath(filename)) as origin:
        # get the file
        destination = directories.user_config_path / filename

        # create directory
        destination.parent.mkdir(parents=True, exist_ok=True)

        # check destination does not exist
        if not force and destination.exists():
            result = strtobool(
                input("{} already exists, overwrite? [y/N] ".format(destination))
            )

            if not result:
                return

        # copy file
        copyfile(origin, destination)
        logger.info("Config created in '%s'", destination)


class ConfigError(DakaraError):
    """Generic error raised for invalid configuration file."""


class ConfigNotFoundError(ConfigError):
    """Unable to read configuration file."""


class ConfigParseError(ConfigError):
    """Unable to parse config file."""


class ConfigInvalidError(ConfigError):
    """Config has missing mandatory keys."""
