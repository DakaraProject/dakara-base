from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

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


class AuthenticatedTestCase(TestCase):
    """Test the `authenticated` decorator."""

    class Authenticated:
        def __init__(self):
            self.token = None

        @authenticated
        def dummy(self):
            pass

    def test_authenticated_sucessful(self):
        """Test the authenticated decorator when token is set."""
        instance = self.Authenticated()

        # set the token
        instance.token = True

        # call a protected method
        instance.dummy()

    def test_authenticated_error(self):
        """Test the authenticated decorator when token is not set."""
        instance = self.Authenticated()

        # call a protected method
        with self.assertRaises(NotAuthenticatedError):
            instance.dummy()


class HTTPClientTestCase(TestCase):
    """Test the HTTP connection with a server."""

    def setUp(self):
        # create a token
        self.token = "token value"

        # create a server URL
        self.url = "http://www.example.com"

        # create a server API URL
        self.url_api = "http://www.example.com/api/"

        # create a server URL endpoint
        self.url_endpoint = "http://www.example.com/api/endpoint/"

        # create login URL
        self.url_login = "http://www.example.com/api/accounts/login/"

        # create a login and password
        self.login = "test"
        self.password = "test"

        # create a ServerHTTPConnection instance
        self.client = HTTPClient(
            {"url": self.url, "login": self.login, "password": self.password},
            endpoint_prefix="api/",
        )

    def set_token(self):
        """Set the token to the test client."""
        self.client.token = self.token

    def set_mute(self):
        """Set the client to mute communication errors when sending requests."""
        self.client.mute_raise = True

    def test_init(self):
        """Test to create object."""
        # use the already created client object
        self.assertEqual(self.client.server_url, self.url_api)
        self.assertEqual(self.client.login, self.login)
        self.assertEqual(self.client.password, self.password)
        self.assertIsNone(self.client.token)

    def test_load_missing_key(self):
        """Test to create object with missing mandatory key."""
        # try to create a client from invalid config
        client = HTTPClient({"url": self.url}, endpoint_prefix="api/")

        with self.assertRaisesRegex(
            ParameterError,
            "You have to either specify 'token' or the couple 'login' "
            "and 'password' in config file",
        ):
            client.load()

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_send_request_raw_successful(self, mocked_post):
        """Test to send a raw request with the generic method."""
        # call the method
        with self.assertLogs("dakara_base.http_client", "DEBUG") as logger:
            self.client.send_request_raw(
                "post",
                "endpoint/",
                data={"content": "test"},
                message_on_error="error message",
            )

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            [
                "DEBUG:dakara_base.http_client:"
                "Sending POST request to http://www.example.com/api/endpoint/"
            ],
        )

        # assert the call
        mocked_post.assert_called_with(
            "http://www.example.com/api/endpoint/", data={"content": "test"}
        )

    def test_send_request_raw_error_method(self):
        """Test that a wrong method name fails for a generic raw request."""
        # call the method
        with self.assertRaises(MethodError):
            self.client.send_request_raw(
                "invalid",
                "endpoint/",
                data={"content": "test"},
                message_on_error="error message",
            )

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_send_request_raw_error_request(self, mocked_post):
        """Test to send a raw request when there is a communication error."""
        # mock the response of the server
        mocked_post.side_effect = RequestException("error")

        # call the method
        with self.assertLogs("dakara_base.http_client", "DEBUG") as logger:
            with self.assertRaisesRegex(
                ResponseRequestError, "Error when communicating with the server: error"
            ):
                self.client.send_request_raw(
                    "post",
                    "endpoint/",
                    data={"content": "test"},
                    message_on_error="error message",
                )

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            [
                "DEBUG:dakara_base.http_client:Sending POST request to "
                "http://www.example.com/api/endpoint/",
                "ERROR:dakara_base.http_client:error message, communication error",
            ],
        )

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_send_request_raw_error_response(self, mocked_post):
        """Test to send a raw request when the response is invalid."""
        # mock the response of the server
        mocked_post.return_value.ok = False

        # call the method
        with self.assertLogs("dakara_base.http_client", "DEBUG"):
            with self.assertRaises(ResponseInvalidError):
                self.client.send_request_raw("post", "endpoint/")

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_send_request_raw_error_response_custom(self, mocked_post):
        """Test to send a raw request when the response is invalid and an
        error function given."""
        # mock the response of the server
        mocked_post.return_value.ok = False

        # create error exception and error function
        class MyError(Exception):
            pass

        def on_error(response):
            return MyError()

        # call the method
        with self.assertLogs("dakara_base.http_client", "DEBUG"):
            with self.assertRaises(MyError):
                self.client.send_request_raw(
                    "post", "endpoint/", function_on_error=on_error
                )

    @patch.object(HTTPClient, "send_request_raw", autospec=True)
    def test_send_request_successful(self, mocked_send_request_raw):
        """Test to send a successful request."""
        # set the token
        self.set_token()

        # call the method
        self.client.send_request("post", "endpoint/", json={"key": "value"})

        # assert the call
        mocked_send_request_raw.assert_called_with(
            self.client,
            "post",
            "endpoint/",
            headers={"Authorization": "Token token value"},
            json={"key": "value"},
        )

    @patch.object(HTTPClient, "send_request_raw", autospec=True)
    def test_send_request_error_raised(self, mocked_send_request_raw):
        """Test to send an unsuccessful request which is not muted."""
        # set the token
        self.set_token()

        # raise an error
        mocked_send_request_raw.side_effect = ResponseInvalidError("invalid")

        # call the method
        with self.assertRaises(ResponseInvalidError):
            self.client.send_request("post", "endpoint/", json={"key": "value"})

    @patch.object(HTTPClient, "send_request_raw", autospec=True)
    def test_send_request_error_muted(self, mocked_send_request_raw):
        """Test to send an unsuccessful request which is muted."""
        # set the token
        self.set_token()
        self.set_mute()

        # raise an error
        mocked_send_request_raw.side_effect = ResponseInvalidError("invalid")

        # call the method
        response = self.client.send_request("post", "endpoint/", json={"key": "value"})

        # assert the response is None
        self.assertIsNone(response)

    @patch("dakara_base.http_client.requests.delete", autospec=True)
    @patch("dakara_base.http_client.requests.patch", autospec=True)
    @patch("dakara_base.http_client.requests.put", autospec=True)
    @patch("dakara_base.http_client.requests.post", autospec=True)
    @patch("dakara_base.http_client.requests.get", autospec=True)
    def test_methods(
        self, mocked_get, mocked_post, mocked_put, mocked_patch, mocked_delete
    ):
        """Test the different HTTP methods."""
        # set the token
        self.set_token()

        # mock the response
        response = MagicMock()
        response.json.return_value = "data"
        mocked_get.return_value = response
        mocked_post.return_value = response
        mocked_put.return_value = response
        mocked_patch.return_value = response
        mocked_delete.return_value = response

        for method in ("get", "post", "put", "patch", "delete"):
            # call the method

            response_obtained = getattr(self.client, method)("endpoint/")

            # assert the result
            self.assertEqual(response_obtained, "data")

        # assert the calls
        mocked_get.assert_called_with(self.url_endpoint, headers=ANY)
        mocked_post.assert_called_with(self.url_endpoint, headers=ANY)
        mocked_put.assert_called_with(self.url_endpoint, headers=ANY)
        mocked_patch.assert_called_with(self.url_endpoint, headers=ANY)
        mocked_delete.assert_called_with(self.url_endpoint, headers=ANY)

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_authenticate_successful(self, mocked_post):
        """Test a successful authentication with the server."""
        # mock the response of the server
        mocked_post.return_value.ok = True
        mocked_post.return_value.json.return_value = {"token": self.token}

        # pre assertions
        self.assertIsNone(self.client.token)

        # call the method
        with self.assertLogs("dakara_base.http_client", "DEBUG") as logger:
            self.client.authenticate()

        # call assertions
        mocked_post.assert_called_with(
            self.url_login, json={"login": self.login, "password": self.password}
        )

        # post assertions
        self.assertIsNotNone(self.client.token)
        self.assertEqual(self.client.token, self.token)

        # assert effect on logger
        self.assertListEqual(
            logger.output,
            [
                "DEBUG:dakara_base.http_client:Authenticate to the server",
                "DEBUG:dakara_base.http_client:"
                "Sending POST request to http://www.example.com/api/accounts/login/",
                "INFO:dakara_base.http_client:Login to server successful",
                "DEBUG:dakara_base.http_client:Token: {}".format(self.token),
            ],
        )

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_authenticate_token_present(self, mocked_post):
        """Test to bypass authentication with already present token."""
        # create token
        self.client.token = self.token

        # call the method
        self.client.authenticate()

        # call assertions
        mocked_post.assert_not_called()

        # post assertions
        self.assertEqual(self.client.token, self.token)

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_authenticate_error_network(self, mocked_post):
        """Test a network error when authenticating."""
        # mock the response of the server
        mocked_post.side_effect = RequestException()

        # call the method
        with self.assertRaises(ResponseRequestError):
            with self.assertLogs("dakara_base.http_client", "DEBUG"):
                self.client.authenticate()

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_authenticate_error_authentication(self, mocked_post):
        """Test an authentication error when authenticating."""
        # mock the response of the server
        mocked_post.return_value.ok = False
        mocked_post.return_value.status_code = 400

        # call the method
        with self.assertRaises(AuthenticationError):
            with self.assertLogs("dakara_base.http_client", "DEBUG"):
                self.client.authenticate()

    @patch("dakara_base.http_client.requests.post", autospec=True)
    def test_authenticate_error_other(self, mocked_post):
        """Test a server error when authenticating."""
        # mock the response of the server
        mocked_post.return_value.ok = False
        mocked_post.return_value.status_code = 999
        mocked_post.return_value.test = "error"

        # call the method
        with self.assertRaises(AuthenticationError):
            with self.assertLogs("dakara_base.http_client", "DEBUG"):
                self.client.authenticate()

    def test_get_token_header(self):
        """Test the helper to get token header."""
        # set the token
        self.set_token()

        # call the method
        result = self.client.get_token_header()

        # call assertions
        self.assertEqual(result, {"Authorization": "Token " + self.token})

    def test_get_json_from_response(self):
        """Test the helper to get data from existing response."""
        # create the mock
        response = MagicMock()

        # call the method
        result = HTTPClient.get_json_from_response(response)

        # assert the result is not None
        self.assertIsNotNone(result)

        # assert the call
        response.json.assert_called_with()

    def test_get_json_from_response_none(self):
        """Test the helper to get data from no response."""
        # call the method
        result = HTTPClient.get_json_from_response(None)

        # assert the result is None
        self.assertIsNone(result)

    def test_get_json_from_response_no_content(self):
        """Test the helper to get data from a response with no content."""
        # create a response with no content
        response = MagicMock()
        response.text = ""
        response.json.side_effect = Exception("error")

        # call the method
        result = HTTPClient.get_json_from_response(response)

        # assert the result is None
        self.assertIsNone(result)
