"""WebSocket client helper module.

This module provides the WebSocket client class WebSocketClient, using the
websocket_client library. The class is designed to work with servers sending
JSON messages. The message received from the server must be handled by custom
methods, consequently the class cannot be used directly:

>>> class MyWebSocketClient(WebSocketClient):
...     def receive_new_song(self, data):
...         pass

The websocket client uses a token to authenticate to the server. The token can
be optained by the `HTTPClient` class from the `http_client` module, with the
`get_token_header` method. The client is a bit complex to setup:

>>> from threading import Event
>>> from queue import Queue
>>> stop = Event()
>>> errors = Queue()
>>> config = {
...     "url": "ws://www.example.com"
... }
>>> header = {
...     "Authorization": "Token my-token-value"
... }
>>> websocket_client = MyWebSocketClient(stop, errors, config,
...                                      endpoint="ws/", header=header)
>>> websocket_client.timer.start()
>>> websocket_client.timer.join()
"""

import json
import logging
from dataclasses import InitVar, dataclass, field
from functools import wraps
from typing import Any, Callable

from websocket import (
    WebSocketApp,
    WebSocketBadStatusException,
    WebSocketConnectionClosedException,
)

from dakara_base.exceptions import DakaraError
from dakara_base.safe_workers import WorkerSafeTimer, safe
from dakara_base.utils import create_url, truncate_message

logger = logging.getLogger(__name__)


RECONNECT_INTERVAL = 5
"""Interval in seconds between two reconnection attempts."""


def connected(fun: Callable) -> Callable:
    """Decorator that ensures the websocket is set.

    It makes sure that the given function is called only if connected.
    If not connected, calling the function will raise a NotConnectedError.
    """

    @wraps(fun)
    def call(self, *args, **kwargs) -> Any:
        if self.websocket is None:
            raise NotConnectedError("No connection established")

        return fun(self, *args, **kwargs)

    return call


@dataclass
class WebSocketClient(WorkerSafeTimer):
    """WebSocket client.

    It communicates with WebSocket messages of a fixed format. The message is a
    JSON string representing a dictionary containing two keys: `type` (str)
    the type of the message, mandatory; and `data` (anything) the content of
    the message, optional. When sending a message, the data cannot be a lone
    None: in this case the key is not present in the message.

    On receiving a message, the client will call the method corresponding to
    its type, which name is `receive_<type of the message here>`. The method
    must accept one argument, which is the `data` key of the message.

    If the client is disconnected to the server, it tries to reconnect every
    `reconnect_interval` seconds.

    Being a `safe_workers.WorkerSafeTimer`, any non caught exception in
    callbacks will stop the entire program. Also, the class is a context
    manager which aborts the connection on exit.
    """

    config: InitVar[dict]
    """Configuration for the server, the same as
    `DakaraServerHTTPConnection`.
    """

    endpoint: InitVar[str | None] = None
    """Enpoint of the WebSocket connection, added to the URL."""

    header: dict = field(default_factory=dict)
    """Header to add to the HTTP requests for authentication."""

    websocket: WebSocketApp | None = field(init=False, default=None)
    """WebSocket connection object."""

    retry: bool = field(init=False, default=False)
    """Flag to retry a connection if it was lost."""

    server_url: str = field(init=False)
    """URL of the server."""

    reconnect_interval: int = field(init=False)
    """Interval in seconds between two reconnection attempts."""

    callbacks: dict[str, Callable] = field(init=False, default_factory=dict)
    """Dictionary of extra callback actions to call on receiving messages."""

    def __post_init__(self, config, endpoint) -> None:
        # url
        self.server_url = create_url(
            **config, path=endpoint or "", scheme_no_ssl="ws", scheme_ssl="wss"
        )

        # other
        self.reconnect_interval = config.get("reconnect_interval", RECONNECT_INTERVAL)

        # create callbacks
        self.set_default_callbacks()

        # create timer
        self.set_timer(0, self.run)

    def set_default_callbacks(self) -> None:
        """Stub for creating callbacks.

        The method is automatically called at initialization.
        """

    def exit_worker(self, *args, **kwargs) -> None:
        """Method called on exiting the worker to abort the connection."""
        logger.debug("Aborting websocket connection")
        self.abort()

    def set_callback(self, name: str, callback: Callable) -> None:
        """Assign an arbitrary callback.

        Callback is added to the `callbacks` dictionary attribute.

        Args:
            name: Name of the callback in the `callbacks` attribute.
            callback: Function to assign.
        """
        self.callbacks[name] = callback

    @safe
    def on_open(self) -> None:
        """Callback when the connection is open."""
        logger.info("Websocket connected to server")
        self.retry = False
        self.on_connected()

    @safe
    def on_close(self, code: int, reason: str) -> None:
        """Callback when the connection is closed.

        If the disconnection is not due to the end of the program, consider the
        connection has been lost. In that case, a reconnection will be
        attempted within `reconnect_interval` seconds.

        Args:
            code: Error code (often None).
            reason: Reason of the closed connection (often None).
        """
        if code or reason:
            logger.debug("Code %i: %s", code, reason)

        # destroy websocket object
        self.websocket = None

        if self.stop.is_set():
            logger.info("Websocket disconnected from server")
            return

        if not self.retry:
            logger.error("Websocket connection lost")

        self.retry = True
        self.on_connection_lost()

        # attempt to reconnect
        logger.warning("Trying to reconnect in %i s", self.reconnect_interval)
        self.timer = self.create_timer(self.reconnect_interval, self.run)
        self.timer.start()

    @safe
    def on_message(self, message: str) -> None:
        """Callback when a message is received.

        It will call the method which name corresponds to the event type, if
        possible. Methods must have the name `receive_<name of the event type
        here>`, the type must be indicated in the `type` key of the message.
        The content of the message must be in the `data` key.

        Any error is logged.

        Args:
            message: A JSON text of the event.
        """
        # convert the message to an event object
        try:
            event = json.loads(message)

        # if the message is not in JSON format, assume this is an error
        except json.JSONDecodeError:
            logger.error(
                "Unexpected message from the server: '%s'", truncate_message(message)
            )
            return

        # get the type of the message
        try:
            message_type = event["type"]

        except KeyError:
            logger.error("Event of no type received")
            return

        # attempt to call the corresponding method
        method_name = "receive_{}".format(message_type)
        try:
            getattr(self, method_name)(event.get("data"))

        except AttributeError:
            logger.error("Event of unknown type received '%s'", message_type)

    @safe
    def on_error(self, error: BaseException) -> None:
        """Callback when an error occurs.

        Args:
            error: Class of the error.

        Raises:
            AuthenticationError: If the connection is denied.
            NetworkError: If the communication cannot be established.
            ParameterError: If the endpoint is invalid.
        """
        # do not analyze error on program exit, as it will mistake the
        # WebSocketConnectionClosedException raised by invoking `abort` for a
        # server connection closed error
        if self.stop.is_set():
            return

        # the connection was refused
        if isinstance(error, WebSocketBadStatusException):
            raise AuthenticationError(
                "Unable to connect to server with this user"
            ) from error

        # the server is unreachable
        if isinstance(error, ConnectionRefusedError):
            if self.retry:
                logger.warning("Unable to talk to the server")
                return

            raise NetworkError("Network error, unable to talk to the server") from error

        # the requested endpoint does not exist
        if isinstance(error, ConnectionResetError):
            raise ParameterError("Invalid endpoint to the server") from error

        # connection closed by the server (see beginning of the method)
        if isinstance(error, WebSocketConnectionClosedException):
            # this case is handled by the on_close method
            return

        # other unlisted reason
        logger.error("Websocket: %s", str(error))

    def on_connected(self) -> None:
        """Custom callback when the connection is established with the server.

        This method is a stub that can be overloaded.
        """

    def on_connection_lost(self) -> None:
        """Custom callback when the connection is lost with the server.

        This method is a stub that can be overloaded.
        """

    @connected
    def send(self, message_type: str, data: Any | None = None, *args, **kwargs) -> None:
        """Send data to the server.

        Convert it to JSON string before sending.

        Args:
            message_type: Type of the message.
            data: Serializable data to send.
            Other arguments are passed to `websocket.WebSocketApp.send`.
        """
        # add type to the content
        content = {"type": message_type}

        # add data to the content if any
        if data is not None:
            content["data"] = data

        assert self.websocket is not None

        return self.websocket.send(json.dumps(content), *args, **kwargs)

    def abort(self) -> None:
        """Request to interrupt the connection.

        Can be called from anywhere. It will raise a
        `WebSocketConnectionClosedException` which will be passed to
        `on_error`.
        """
        self.retry = False

        if self.websocket is None:
            return

        # if the connection is lost, the `websocket` object may not have the
        # `abort` method
        if self.websocket.sock is not None:
            self.websocket.sock.abort()

    def run(self) -> None:
        """Event loop.

        Create the websocket connection and wait events from it. The method can
        be interrupted with the `abort` method.

        The WebSocketApp class is a genki: It will never complain of anything.
        Wether it is unable to create a connection or its connection is lost,
        the `run_forever` method ends without any exception or non-None return
        value. Exceptions are handled by the yandere `on_error` callback.
        """
        logger.debug("Preparing websocket connection")
        self.websocket = WebSocketApp(
            self.server_url,
            header=self.header,
            on_open=lambda ws: self.on_open(),
            on_close=lambda ws, code, reason: self.on_close(code, reason),
            on_message=lambda ws, message: self.on_message(message),
            on_error=lambda ws, error: self.on_error(error),
        )
        self.websocket.run_forever()


class NotConnectedError(DakaraError):
    """Error raised when connection is missing."""


class AuthenticationError(DakaraError):
    """Error raised when authentication fails."""


class ParameterError(DakaraError, ValueError):
    """Error raised when server parameters are unproperly set."""


class NetworkError(DakaraError):
    """Error raised when unable to communicate with the server."""
