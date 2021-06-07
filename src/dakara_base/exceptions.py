"""Exceptions helper module.

This module defines the base exception class for any project using this
library. All exception classes should inherit from `DakaraError`:

>>> class MyError(DakaraError):
...     pass

This helps to differentiate known exceptions and unknown ones, which are real
bugs. On program execution, a try/except structure determines the reason of
interruption of the program:

>>> import logging
>>> debug = False
>>> try:
...     # your program here
... except KeyboardInterrupt:
...     logging.info("Quit by user")
...     exit(255)
... except SystemExit:
...     logging.info("Quit by system")
...     exit(254)
... except DakaraError as error:
...     # known error
...     if debug:
...         # directly re-raise the error in debug mode
...         raise
...     # just log it otherwise
...     logging.critical(error)
...     exit(1)
... except BaseException as error:
...     # unknown error
...     if debug:
...         # directly re-raise the error in debug mode
...         raise
...     # re-raise it and show a special message otherwise
...     logging.exception("Unexpected error: {}".format(error))
...     logging.critical("Please fill a bug report at <url of bugtracker>")
...     exit(128)
>>> exit(0)
"""


class DakaraError(Exception):
    """Basic exception class for the project."""
