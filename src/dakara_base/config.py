"""Config helper module

This module gives a config loader function `load_config` that reads a YAML
config file:

>>> from path import Path
>>> config = load_config(Path("path/to/file.yaml"), debug=True)

The module has two functions to configure loaders: `create_logger`, which
installs the logger using coloredlogs, and `set_loglevel`, which sets the
loglevel of the logger according to the config. Usually, you call the first one
before reading the config, as `load_config` needs a logger, then call the
latter one:

>>> create_logger()
>>> from path import Path
>>> config = load_config(Path("path/to/file.yaml"), debug=True)
>>> set_loglevel(config)

If you use progress bar and logging at the same time, you should call
`create_logger` with `wrap=True`.

The module has three functions to manage Dakara Project config files. First,
`get_config_directory` gives the configuration directory according to the
operating system. Next, `get_config_file` gives the complete path to the config
file in the configuration directory:

>>> config_path = get_config_file("my_config.yaml")

Then, `create_config` copies a given config file stored in module resources to
the configuration directory:

>>> create_config("module.resources", "my_config.yaml")
"""


import logging
import sys
from distutils.util import strtobool

import coloredlogs
import progressbar
import yaml
from path import Path

try:
    from importlib.resources import path

except ImportError:
    from importlib_resources import path

from dakara_base.exceptions import DakaraError

LOG_FORMAT = "[%(asctime)s] %(name)s %(levelname)s %(message)s"
LOG_LEVEL = "INFO"


logger = logging.getLogger(__name__)


def load_config(config_path, debug, mandatory_keys=None):
    """Load config from given YAML file

    Args:
        config_path (path.Path): path to the config file.
        debug (bool): run in debug mode. This creates or overwrites the
            `loglovel` key of the config to "DEBUG".
        mandatory_keys (list): list of keys that must be present at the root
            level of the config.

    Returns:
        dict: dictionary of the config.

    Raises:
        ConfigNotFoundError: if the config file cannot be open.
        ConfigParseError: if the config cannot be parsed.
        ConfigInvalidError: if the config misses critical sections.
    """
    logger.info("Loading config file '%s'", config_path)

    # load and parse the file
    try:
        with config_path.open() as file:
            try:
                config = yaml.load(file, Loader=yaml.Loader)

            except yaml.parser.ParserError as error:
                raise ConfigParseError("Unable to parse config file") from error

    except FileNotFoundError as error:
        raise ConfigNotFoundError("No config file found") from error

    # if requested check file content
    if mandatory_keys:
        for key in mandatory_keys:
            if key not in config:
                raise ConfigInvalidError(
                    "Invalid config file, missing '{}'".format(key)
                )

    # if debug is set as argument, override the config
    if debug:
        config["loglevel"] = "DEBUG"

    return config


def create_logger(wrap=False, custom_log_format=None, custom_log_level=None):
    """Create logger

    Args:
        wrap (bool): if True, wrap the standard error stream for using logging
            and progress bar. You have to enable this flag if you use
            `progress_bar`.
        custom_log_format (str): custom format string to use for logs.
        custom_log_level (str): custom level of logging.
    """
    # wrap stderr on demand
    if wrap:
        progressbar.streams.wrap_stderr()

    # setup loggers
    log_format = custom_log_format or LOG_FORMAT
    log_level = custom_log_level or LOG_LEVEL
    coloredlogs.install(fmt=log_format, level=log_level)


def set_loglevel(config):
    """Set logger level

    Arguments:
        config (dict): dictionary of the config.
    """
    loglevel = config.get("loglevel", LOG_LEVEL)
    coloredlogs.set_level(loglevel)


def get_config_directory():
    """Returns the Dakara config directory to use for the current OS

    Returns:
        path.Path: path of the Dakara config directory. Value is not expanded,
        so you have to call `.expand()` on the return value.
    """
    if "linux" in sys.platform:
        return Path("~") / ".config" / "dakara"

    if "win" in sys.platform:
        return Path("$APPDATA") / "Dakara"

    raise NotImplementedError(
        "This operating system ({}) is not currently supported".format(sys.platform)
    )


def create_config_file(resource, filename, force=False):
    """Create a new config file in user directory

    Args:
        resource (str): resource where to find the config file.
        filename (str): name of the config file.
        force (bool): if True, config file in user directory is overwritten if
            it existed already. Otherwise, prompt the user.
    """
    with path(resource, filename) as file:
        # get the file
        origin = Path(file)
        destination = get_config_file(filename)

        # create directory
        destination.dirname().mkdir_p()

        # check destination does not exist
        if not force and destination.exists():
            try:
                result = strtobool(
                    input("{} already exists, overwrite? [y/N] ".format(destination))
                )

            except ValueError:
                result = False

            if not result:
                return

        # copy file
        origin.copyfile(destination)
        logger.info("Config created in '{}'".format(destination))


def get_config_file(filename):
    """Get path of the config in user directory

    It does not check if the file exists.

    Args:
        filename (str): name of the config file.

    Returns:
        path.Path: path to the config file.
    """
    directory = get_config_directory().expand()
    return directory / filename


class ConfigError(DakaraError):
    """Generic error raised for invalid configuration file
    """


class ConfigNotFoundError(ConfigError):
    """Unable to read configuration file
    """


class ConfigParseError(ConfigError):
    """Unable to parse config file
    """


class ConfigInvalidError(ConfigError):
    """Config has missing mandatory keys
    """
