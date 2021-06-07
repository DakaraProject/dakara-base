"""Utils helper module.

This module regroups diverse helper functions.

The `truncate_message` function truncates a string if its width is langer than a
certain limit:

>>> string = "Lorem ipsum dolot sit amet."
>>> truncate_message(string, limit=15)
"Lorem ipsum..."

It was initialy designed to cut Django responses during development, as some
internal errors could make the server to respond by a very long HTML message,
polluting the logs.

The `create_url` is an URL creator build on top of the furl module. It is
typically designed to take a server config and forge an URL from it, wether the
URL is explicitally defined, or its components are individually defined, such
as host, port, etc.:

>>> config = {
...     "address": "www.example.com:8080",
...     "ssl": True,
...     "path": "api/",
... }
>>> create_url(**config)
"https://www.example.com:8080/api/"
"""
from furl import furl

from dakara_base.exceptions import DakaraError


def truncate_message(message, limit=100):
    """Display the first characters of a message.

    The message is truncated using ellipsis and stripped to avoid blank spaces
    before the ellipsis.

    Args:
        message (str): Message to truncate.
        limit (int): Maximum size of the message.

    Returns:
        str: Truncated message.
    """
    assert limit - 3 > 0, "Limit too short"

    if len(message) <= limit:
        return message

    return message[: limit - 3].strip() + "..."


def create_url(
    url="",
    address="",
    host="",
    port=None,
    path="",
    ssl=False,
    scheme_no_ssl="http",
    scheme_ssl="https",
    **kwargs
):
    """Create an URL from arguments.

    If `url` is given, the function returns it with `path` appended. If no
    `host` is given, `host` and `port` are extracted from `address` with the
    `host:port` format.  If `ssl` is given and True, `scheme_ssl` is used,
    otherewise `scheme_no_ssl` is used.  If `path` is given, it is appended to
    the URL.

    Args:
        url (str): Direct URL.
        address (str): Host, or host and port.
        host (str): Host.
        port (str): Port.
        path (str): Path appended to the URL.
        ssl (bool): Use a secured URL or not.
        scheme_no_ssl (str): Scheme used if `ssl` is false.
        scheme_ssl (str): Scheme used if `ssl` is true.
        Any other argument is ignored.

    Returns:
        str: URL string.

    Raises:
        URLParameterError: If `scheme` or `host` cannot be defined, or if the
            parameters are invalid to `furl.furl`.
    """
    # setting URL directly
    if url:
        return furl(url).add(path=path).url

    # getting host and port indirectly from address
    if not host:
        # try to separete host and port if they are both given in
        # address key in the form host:port
        try:
            host, port = address.split(":")

        except ValueError:
            host = address

    # getting scheme
    if ssl:
        scheme = scheme_ssl

    else:
        scheme = scheme_no_ssl

    # check mandatory arguments are given
    if not (scheme and host):
        raise URLParameterError(
            "Unable to set mandatory arguments for URL in server config, please check "
            "'url', 'address', 'host', 'port' and/or 'ssl'"
        )

    # combine the arguments
    try:
        return furl(scheme=scheme, host=host, port=port, path=path).url

    except ValueError as error:
        raise URLParameterError(
            "Error when setting URL in server config: {}".format(error)
        ) from error


class URLParameterError(DakaraError, ValueError):
    """Error raised when server parameters are unproperly set."""
