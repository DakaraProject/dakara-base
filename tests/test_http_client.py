import logging
from dataclasses import dataclass
from unittest.mock import ANY, MagicMock

import pytest
from requests.exceptions import RequestException

from dakara_base.http_client import (
    AuthenticationError,
    HTTPClient,
    MethodError,
    NotAuthenticatedError,
    ParameterError,
    ResponseInvalidError,
    ResponseRequestError,
    authenticated,
)


@dataclass
class Authenticated:
    token: str | None = None

    @authenticated
    def dummy(self) -> None:
        pass


@pytest.fixture
def authenticated() -> Authenticated:
    return Authenticated()


class TestAuthenticated:

    def test_authenticated_sucessful(self, authenticated):
        """Test the authenticated decorator when token is set."""
        # set the token
        authenticated.token = True

        # call a protected method
        authenticated.dummy()

    def test_authenticated_error(self, authenticated):
        """Test the authenticated decorator when token is not set."""
        # call a protected method
        with pytest.raises(NotAuthenticatedError):
            authenticated.dummy()


@pytest.fixture
def http_client() -> HTTPClient:
    return HTTPClient(
        {"url": "http://www.example.com", "login": "login", "password": "password"},
        endpoint_prefix="api",
    )


@pytest.fixture
def http_client_token() -> HTTPClient:
    return HTTPClient(
        {
            "url": "http://www.example.com",
            "login": "login",
            "password": "password",
            "token": "token value",
        },
        endpoint_prefix="api",
    )


@pytest.fixture
def http_client_token_mute() -> HTTPClient:
    return HTTPClient(
        {
            "url": "http://www.example.com",
            "login": "login",
            "password": "password",
            "token": "token value",
        },
        endpoint_prefix="api",
        mute_raise=True,
    )


class TestHTTPClient:
    def test_init(self, http_client):
        """Test to create object."""
        assert http_client.server_url == "http://www.example.com/api"
        assert http_client.login == "login"
        assert http_client.password == "password"
        assert http_client.token is None

    def test_load_missing_key(self):
        """Test to create object with missing mandatory key."""
        # try to create a client from invalid config
        client = HTTPClient({"url": "http://www.example.com"}, endpoint_prefix="api/")

        with pytest.raises(
            ParameterError,
            match="You have to either specify 'token' or the couple 'login' "
            "and 'password' in config file",
        ):
            client.load()

    def test_send_request_raw_successful(self, http_client, caplog, mocker):
        """Test to send a raw request with the generic method."""
        caplog.set_level(logging.DEBUG)
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )

        # call the method
        http_client.send_request_raw(
            "post",
            "endpoint/",
            data={"content": "test"},
            message_on_error="error message",
        )

        # assert the effect on logger
        assert caplog.record_tuples == [
            (
                "dakara_base.http_client",
                logging.DEBUG,
                "Sending POST request to http://www.example.com/api/endpoint/",
            )
        ]

        # assert the call
        mocked_post.assert_called_with(
            "http://www.example.com/api/endpoint/", data={"content": "test"}
        )

    def test_send_request_raw_error_method(self, http_client):
        """Test that a wrong method name fails for a generic raw request."""
        # call the method
        with pytest.raises(MethodError):
            http_client.send_request_raw(
                "invalid",
                "endpoint/",
                data={"content": "test"},
                message_on_error="error message",
            )

    def test_send_request_raw_error_request(self, http_client, caplog, mocker):
        """Test to send a raw request when there is a communication error."""
        mocker.patch(
            "dakara_base.http_client.requests.post",
            autospec=True,
            side_effect=RequestException("error"),
        )
        caplog.set_level(logging.DEBUG)

        # call the method
        with pytest.raises(
            ResponseRequestError,
            match="Error when communicating with the server: error",
        ):
            http_client.send_request_raw(
                "post",
                "endpoint/",
                data={"content": "test"},
                message_on_error="error message",
            )

        # assert the effect on logger
        assert caplog.record_tuples == [
            (
                "dakara_base.http_client",
                logging.DEBUG,
                "Sending POST request to http://www.example.com/api/endpoint/",
            ),
            (
                "dakara_base.http_client",
                logging.ERROR,
                "error message, communication error",
            ),
        ]

    def test_send_request_raw_error_response(self, http_client, caplog, mocker):
        """Test to send a raw request when the response is invalid."""
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )
        mocked_post.return_value.ok = False
        caplog.set_level(logging.DEBUG)

        # call the method
        with pytest.raises(ResponseInvalidError):
            http_client.send_request_raw("post", "endpoint/")

    def test_send_request_raw_error_response_custom(self, http_client, caplog, mocker):
        """Test to send a raw request when the response is invalid and an
        error function given."""
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )
        mocked_post.return_value.ok = False
        caplog.set_level(logging.DEBUG)

        # create error exception and error function
        class MyError(Exception):
            pass

        def on_error(response):
            return MyError()

        # call the method
        with pytest.raises(MyError):
            http_client.send_request_raw(
                "post", "endpoint/", function_on_error=on_error
            )

    def test_send_request_successful(self, http_client_token, mocker):
        """Test to send a successful request."""
        mocked_send_request_raw = mocker.patch.object(
            HTTPClient, "send_request_raw", autospec=True
        )

        # call the method
        http_client_token.send_request("post", "endpoint/", json={"key": "value"})

        # assert the call
        mocked_send_request_raw.assert_called_with(
            http_client_token,
            "post",
            "endpoint/",
            headers={"Authorization": "Token token value"},
            json={"key": "value"},
        )

    def test_send_request_error_raised(self, http_client_token, mocker):
        """Test to send an unsuccessful request which is not muted."""
        mocker.patch.object(
            HTTPClient,
            "send_request_raw",
            autospec=True,
            side_effect=ResponseInvalidError("invalid"),
        )

        # call the method
        with pytest.raises(ResponseInvalidError):
            http_client_token.send_request("post", "endpoint/", json={"key": "value"})

    def test_send_request_error_muted(self, http_client_token_mute, mocker):
        """Test to send an unsuccessful request which is muted."""
        mocker.patch.object(
            HTTPClient,
            "send_request_raw",
            autospec=True,
            side_effect=ResponseRequestError("invalid"),
        )

        # call the method
        response = http_client_token_mute.send_request(
            "post", "endpoint/", json={"key": "value"}
        )

        # assert the response is None
        assert response is None

    def test_methods(self, http_client_token, mocker):
        """Test the different HTTP methods."""
        for method in ("get", "post", "put", "patch", "delete"):
            mocked_method = mocker.patch(
                f"dakara_base.http_client.requests.{method}", autospec=True
            )
            mocked_method.return_value.json.return_value = f"data {method}"

            # call the method
            response_obtained = getattr(http_client_token, method)("endpoint/")

            # assert the result
            assert response_obtained == f"data {method}"

            # assert the calls
            mocked_method.assert_called_with(
                "http://www.example.com/api/endpoint/", headers=ANY
            )

    def test_authenticate_successful(self, http_client, caplog, mocker):
        """Test a successful authentication with the server."""
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )
        mocked_post.return_value.ok = True
        mocked_post.return_value.json.return_value = {"token": "token value"}
        caplog.set_level(logging.DEBUG)

        # pre assertions
        assert http_client.token is None

        # call the method
        http_client.authenticate()

        # call assertions
        mocked_post.assert_called_with(
            "http://www.example.com/api/accounts/login/",
            json={"login": "login", "password": "password"},
        )

        # post assertions
        assert http_client.token == "token value"

        # assert effect on logger
        assert caplog.record_tuples == [
            (
                "dakara_base.http_client",
                logging.DEBUG,
                "Authenticate to the server",
            ),
            (
                "dakara_base.http_client",
                logging.DEBUG,
                "Sending POST request to http://www.example.com/api/accounts/login/",
            ),
            (
                "dakara_base.http_client",
                logging.INFO,
                "Login to server successful",
            ),
            ("dakara_base.http_client", logging.DEBUG, "Token: token value"),
        ]

    def test_authenticate_token_present(self, http_client_token, mocker):
        """Test to bypass authentication with already present token."""
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )

        # call the method
        http_client_token.authenticate()

        # call assertions
        mocked_post.assert_not_called()

        # post assertions
        assert http_client_token.token == "token value"

    def test_authenticate_error_network(self, http_client, mocker):
        """Test a network error when authenticating."""
        mocker.patch(
            "dakara_base.http_client.requests.post",
            autospec=True,
            side_effect=RequestException(),
        )

        # call the method
        with pytest.raises(ResponseRequestError):
            http_client.authenticate()

    def test_authenticate_error_authentication(self, http_client, mocker):
        """Test an authentication error when authenticating."""
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )
        mocked_post.return_value.ok = False
        mocked_post.return_value.status_code = 400

        # call the method
        with pytest.raises(AuthenticationError):
            http_client.authenticate()

    def test_authenticate_error_other(self, http_client, mocker):
        """Test a server error when authenticating."""
        mocked_post = mocker.patch(
            "dakara_base.http_client.requests.post", autospec=True
        )
        mocked_post.return_value.ok = False
        mocked_post.return_value.status_code = 999
        mocked_post.return_value.test = "error"

        # call the method
        with pytest.raises(AuthenticationError):
            http_client.authenticate()

    def test_get_token_header(self, http_client_token):
        """Test the helper to get token header."""
        assert http_client_token.get_token_header() == {
            "Authorization": "Token token value"
        }

    def test_get_json_from_response(self):
        """Test the helper to get data from existing response."""
        # create the mock
        response = MagicMock()
        response.text = "aa"
        response.json.return_value = "bb"

        assert HTTPClient.get_json_from_response(response) == "bb"

    def test_get_json_from_response_none(self):
        """Test the helper to get data from no response."""
        assert HTTPClient.get_json_from_response(None) is None

    def test_get_json_from_response_no_content(self):
        """Test the helper to get data from a response with no content."""
        # create a response with no content
        response = MagicMock()
        response.text = ""
        response.json.side_effect = Exception("error")

        # call the method
        assert HTTPClient.get_json_from_response(response) is None
