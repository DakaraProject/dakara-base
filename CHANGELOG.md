# Changelog

<!---
## 0.0.1 - 1970-01-01

### Added

- New stuff.

### Changed

- Changed stuff.

### Deprecated

- Deprecated stuff.

### Removed

- Removed stuff.

### Fixed

- Fixed stuff.

### Security

- Security related fix.
-->

## Unreleased

### Added

- `config.Config` object to store config.
  Config can be loaded from a file (once).
  When accessing a value, it is first searched in environment variables, then in stored values.

### Changed

- `config.load_config` was integrated in `config.Config` as method `load_file`.
  Its different actions were divided:
  - Loading the config file: `config.Config.load_file`;
  - Checking mandatory keys: `config.Config.check_mandatory_keys`; and
  - Setting debug mode: `config.Config.set_debug`.

### Removed

- Dropped Python 3.5 support.

## 1.3.0 - 2021-04-10

### Changed

- Enpoint for HTTP client authenticated is stored in `dakara_base.http_client.HTTPClient.AUTHENTICATE_ENDPOINT` and can be edited.
  Default value was updated to `accounts/login/`.

### Removed

- Removed module `resources_manager`.
  Use the standard `importlib.resources` instead.

## 1.2.0 - 2019-11-10

### Added

- You can now specify custom log format and log level in `dakara_base.config.create_logger` with arguments `custom_log_format` and `custom_log_level`.
- Access to and create user-level stored Dakara config files with `dakara_base.config.get_config_file` and `dakara_base.config.create_config_file`.

### Changed

- `progress_bar`: the progress bar now displays percentage.

### Fixed

- `progress_bar`: When an exception was raised within a progress bar, it would prevent to stop the capture of stderr, leading to hide any further log entry.

## 1.1.0 - 2019-09-16

### Added

* `progress_bar`: a collection of progress bars.

### Fixed

* Add `safe_workers` in the readme.

## 1.0.1 - 2019-09-08

### Fixed

- Fixed a bug when dealing with a HTTP route that does not have a content.

## 1.0.0 - 2019-07-20

Initial release.

### Added

* `config`: a configuration helper that can load an YAML file and manage loggers;
* `exceptions`: a base class for exceptions;
* `http_client`: an HTTP client dedicated to be used with an API;
* `resources_manager`: a helper for retreiving static files with module-like naming;
* `utils`: other various helpers;
* `websocket_client`: a Websocket client.
