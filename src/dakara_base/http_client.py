"""HTTP client helper module.

This module provides the HTTP client class `HTTPClient`, built on the requests
library. The class is designed to be used with an API which communicates with
JSON messages.  It is pretty straightforward to use:

>>> config = {
...     "url": "http://www.example.com",
...     "login": "login here",
...     "password": "password here",
... }
>>> client = HTTPClient(config, endpoint_prefix="api/")
>>> client.authenticate()  # doctest: +SKIP
>>> data = client.get("library/songs/")  # doctest: +SKIP
>>> client.post("library/songs", json={"title": "some title"})  # doctest: +SKIP
"""

import logging
from dataclasses import InitVar, dataclass, field
from functools import wraps
from typing import Any, Callable, ClassVar

import requests
from furl import furl

from dakara_base.exceptions import DakaraError
from dakara_base.utils import create_url, truncate_message

logger = logging.getLogger(__name__)


def authenticated(fun: Callable) -> Callable:
    """Decorator that ensures the token is set.

    It makes sure that the given function is called only if authenticated. If
    not authenticated, calling the function will raise a `NotAuthenticatedError`.
    """

    @wraps(fun)
    def call(self, *args, **kwargs) -> Any:
        if self.token is None:
            raise NotAuthenticatedError("No connection established")

        return fun(self, *args, **kwargs)

    return call


@dataclass
class HTTPClient:
    """HTTP client designed to work with an API.

    The API must use JSON for message content.

    The client uses a token credential policy only and authenticates with a
    traditional login/password mechanism. If a token is provided, it will be
    used without trying to authenticate.
    """

    AUTHENTICATE_ENDPOINT: ClassVar[str] = "accounts/login/"
    """Endpoint for authentication."""

    config: InitVar[dict]
    """Config of the server."""

    endpoint_prefix: InitVar[str] = None
    """Prefix of the endpoint, added to the URL."""

    mute_raise: bool = False
    """If `True`, no exception will be raised when performing connections with
    the server (but authentication), only logged.
    """

    server_url: str = field(init=False)
    """URL of the server."""

    token: str = field(init=False)
    """Value of the token. The token is set when successfuly calling
    `authenticate`.
    """

    login: str = field(init=False)
    """Login used for authentication."""

    password: str = field(init=False)
    """Password used for authentication."""

    def __post_init__(self, config, endpoint_prefix) -> None:
        # url
        self.server_url = create_url(**config, path=endpoint_prefix or "")

        # authentication
        self.token = config.get("token")
        self.login = config.get("login")
        self.password = config.get("password")

    def load(self) -> None:
        """Perform side effect actions.

        Raises:
            ParameterError: If there is neither a token or a couple
                login/password set.
        """
        if not self.token and not (self.login and self.password):
            raise ParameterError(
                "You have to either specify 'token' or the couple 'login' "
                "and 'password' in config file"
            )

    def send_request_raw(
        self,
        method: str,
        endpoint: str,
        *args,
        message_on_error: str = "",
        function_on_error: Callable[[requests.Response], BaseException] | None = None,
        **kwargs,
    ) -> requests.models.Response:
        """Generic method to send requests to the server.

        It takes care of errors and raises exceptions.

        Args:
            method: Name of the HTTP method to use.
            endpoint: Endpoint to send the request to. Will be added to
                the end of the server URL.
            message_on_error: Message to display in logs in case of
                error. It should describe what the request was about.
            function_on_error: Fuction called if the request is not
                successful, it will receive the response and must return an
                exception that will be raised. If not provided, a basic error
                management is done.
            Extra arguments are passed to requests' get/post/put/patch/delete
                methods.

        Returns:
            Response object.

        Raises:
            MethodError: If the method is not supported.
            ResponseRequestError: For any error when communicating with the server.
            ResponseInvalidError: If the response has an error code different
                to 2**.
        """
        # handle method function
        if not hasattr(requests, method):
            raise MethodError("Method {} not supported".format(method))

        send_method = getattr(requests, method)

        # handle message on error
        if not message_on_error:
            message_on_error = "Unable to request the server"

        # forge URL
        url = furl(self.server_url).add(path=endpoint).url
        logger.debug("Sending %s request to %s", method.upper(), url)

        try:
            # send request to the server
            response = send_method(url, *args, **kwargs)

        except requests.exceptions.RequestException as error:
            # handle connection error
            logger.error("%s, communication error", message_on_error)
            raise ResponseRequestError(
                "Error when communicating with the server: {}".format(error)
            ) from error

        # return here if the request was made without error
        if response.ok:
            return response

        # otherwise call custom error management function
        if function_on_error:
            raise function_on_error(response)

        # otherwise manage error generically
        logger.error(message_on_error)
        logger.debug(
            "Error %i: %s", response.status_code, truncate_message(response.text)
        )

        raise ResponseInvalidError(
            "Error {} when communicationg with the server: {}".format(
                response.status_code, response.text
            )
        )

    @authenticated
    def send_request(self, *args, **kwargs) -> requests.models.Response | None:
        """Generic method to send requests to the server when connected.

        It adds token header for authentication and takes care of errors.
        If `mute_raise` is set, no exceptions are raised in case of error when
        communicating with the server.

        Args:
            See `send_request_raw`.

        Returns:
            Response object. None if an error occurs when communicating with
            the server and `mute_raise` is set.
        """
        try:
            # make the request
            return self.send_request_raw(
                *args, headers=self.get_token_header(), **kwargs
            )

        # manage request error
        except ResponseError:
            if self.mute_raise:
                return None

            raise

    def get(self, *args, **kwargs) -> Any:
        """Generic method to get data on server.

        Args:
            See `send_request`. Extra arguments are passed to requests' get
            method.

        Returns:
            Response object from the server.
        """
        return self.get_json_from_response(self.send_request("get", *args, **kwargs))

    def post(self, *args, **kwargs) -> Any:
        """Generic method to post data on server.

        Args:
            See `send_request`. Extra arguments are passed to requests' post
            method.

        Returns:
            Response object from the server.
        """
        return self.get_json_from_response(self.send_request("post", *args, **kwargs))

    def put(self, *args, **kwargs) -> Any:
        """Generic method to put data on server.

        Args:
            See `send_request`. Extra arguments are passed to requests' put
            method.

        Returns:
            Response object from the server.
        """
        return self.get_json_from_response(self.send_request("put", *args, **kwargs))

    def patch(self, *args, **kwargs) -> Any:
        """Generic method to patch data on server.

        Args:
            See `send_request`. Extra arguments are passed to requests' patch
            method.

        Returns:
            Response object from the server.
        """
        return self.get_json_from_response(self.send_request("patch", *args, **kwargs))

    def delete(self, *args, **kwargs) -> Any:
        """Generic method to patch data on server.

        Args:
            See `send_request`. Extra arguments are passed to requests' delete
            method.

        Returns:
            Response object from the server.
        """
        return self.get_json_from_response(self.send_request("delete", *args, **kwargs))

    def authenticate(self) -> None:
        """Authenticate with the server.

        The authentication process relies on login/password which gives an
        authentication token. This token is stored in the instance.

        If a token was specified in the config, this function does nothing.
        """

        if self.token:
            return

        data = {"login": self.login, "password": self.password}

        def on_error(response) -> AuthenticationError:
            # manage failed connection response
            if response.status_code == 400:
                return AuthenticationError(
                    "Login to server failed, check the config file"
                )

            # manage any other error
            return AuthenticationError(
                "Unable to authenticate to the server, error {code}: {message}".format(
                    code=response.status_code, message=truncate_message(response.text)
                )
            )

        # connect to the server with login/password
        logger.debug("Authenticate to the server")
        response = self.send_request_raw(
            "post",
            self.AUTHENTICATE_ENDPOINT,
            message_on_error="Unable to authenticate to the server",
            function_on_error=on_error,
            json=data,
        )

        # store token
        self.token = response.json().get("token")
        logger.info("Login to server successful")
        logger.debug("Token: %s", self.token)

    @authenticated
    def get_token_header(self) -> dict[str, str]:
        """Get the connection token as it should appear in the header.

        Can be called only after a successful authentication.

        Returns:
            Formatted token.
        """
        return {"Authorization": "Token " + self.token}

    @staticmethod
    def get_json_from_response(
        response: requests.Response | None,
    ) -> Any:
        """Parse the response of a request if possible.

        Args:
            response: Response of a request.

        Returns:
            Parsed response. None if no response was given or response has no
            content.
        """
        if response is not None and response.text:
            return response.json()

        return None


class ResponseError(DakaraError):
    """Generic error when communicating with the server."""


class ResponseRequestError(ResponseError):
    """Error when sending request to the server."""


class ResponseInvalidError(ResponseError):
    """Error with the request sent to the server."""


class AuthenticationError(ResponseInvalidError):
    """Error raised when authentication fails."""


class ParameterError(DakaraError, ValueError):
    """Error raised when server parameters are unproperly set."""


class MethodError(DakaraError, ValueError):
    """Error raised when using an unsupported method."""


class NotAuthenticatedError(DakaraError):
    """Error raised when authentication is missing."""
