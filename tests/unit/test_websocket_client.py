import json
from queue import Queue
from threading import Event
from unittest import TestCase
from unittest.mock import ANY, MagicMock, patch

from websocket import WebSocketBadStatusException, WebSocketConnectionClosedException

from dakara_base.websocket_client import (
    AuthenticationError,
    NetworkError,
    NotConnectedError,
    ParameterError,
    WebSocketClient,
    connected,
)


class ConnectedTestCase(TestCase):
    """Test the `connected` decorator."""

    class Connected:
        def __init__(self):
            self.websocket = None

        @connected
        def dummy(self):
            pass

    def test_connected_sucessful(self):
        """Test the connected decorator when websocket is set.

        Use the `run` method for the test.
        """
        instance = self.Connected()

        # set the token
        instance.websocket = True

        # call a protected method
        instance.dummy()

    def test_connected_error(self):
        """Test the connected decorator when token is not set.

        Use the interal `get_token_header` method for test.
        """
        instance = self.Connected()

        # call a protected method
        with self.assertRaises(NotConnectedError):
            instance.dummy()


class WebSocketClientTestCase(TestCase):
    """Test the WebSocket connection with the server."""

    def setUp(self):
        # create a mock websocket
        self.websocket = MagicMock()

        # create a server URL
        self.url = "ws://www.example.com"

        # create a server WS endpoint URL
        self.url_ws = "ws://www.example.com/ws/"

        # create token header
        self.header = {"token": "token"}

        # create a reconnect interval
        self.reconnect_interval = 1

        # create stop event and errors queue
        self.stop = Event()
        self.errors = Queue()

        # create a DakaraServerWebSocketConnection instance
        self.client = WebSocketClient(
            self.stop,
            self.errors,
            {"url": self.url, "reconnect_interval": self.reconnect_interval},
            header=self.header,
            endpoint="ws/",
        )

    def set_websocket(self):
        """Set the websocket object to a mock."""
        self.client.websocket = MagicMock()

    @patch.object(WebSocketClient, "set_default_callbacks", autospec=True)
    def test_init_worker(self, mocked_set_default_callbacks):
        """Test the initialization."""
        # create the object
        client = WebSocketClient(self.stop, self.errors, {"url": self.url})

        # assert the call
        mocked_set_default_callbacks.assert_called_once_with(client)

        # use the already created client object
        self.assertEqual(self.client.server_url, self.url_ws)
        self.assertEqual(self.client.header, self.header)
        self.assertEqual(self.client.reconnect_interval, self.reconnect_interval)
        self.assertIsNone(self.client.websocket)

    def test_set_callback(self):
        """Test the assignation of a callback."""
        # create a callback function
        callback = MagicMock()

        # pre assert the callback is not set yet
        self.assertIsNot(self.client.callbacks.get("test"), callback)

        # call the method
        self.client.set_callback("test", callback)

        # post assert the callback is now set
        self.assertIs(self.client.callbacks.get("test"), callback)

    @patch.object(WebSocketClient, "abort", autospec=True)
    def test_exit_worker(self, mocked_abort):
        """Test to exit the worker."""
        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.exit_worker()

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            ["DEBUG:dakara_base.websocket_client:Aborting websocket connection"],
        )

        # assert the call
        mocked_abort.assert_called_with(self.client)

    @patch.object(WebSocketClient, "on_connected", autospec=True)
    def test_on_open(self, mocked_on_connected):
        """Test the callback on connection open."""
        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_open()

        # assert the effect
        self.assertFalse(self.client.retry)

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            ["INFO:dakara_base.websocket_client:Websocket connected to server"],
        )

        # assert the call
        mocked_on_connected.assert_called_with(self.client)

    @patch.object(WebSocketClient, "create_timer")
    @patch.object(WebSocketClient, "on_connection_lost")
    def test_on_close_normal(self, mocked_on_connection_lost, mocked_create_timer):
        """Test the callback on connection close when the program is closing."""
        # create the websocket
        self.set_websocket()

        # pre assert
        self.assertIsNotNone(self.client.websocket)
        self.assertFalse(self.client.retry)

        # set the program is closing
        self.stop.set()

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_close(999, "reason")

        # assert the websocket object has been destroyed
        self.assertIsNone(self.client.websocket)
        self.assertFalse(self.client.retry)

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            [
                "DEBUG:dakara_base.websocket_client:Code 999: reason",
                "INFO:dakara_base.websocket_client:Websocket disconnected from server",
            ],
        )

        # assert the call
        mocked_create_timer.assert_not_called()
        mocked_on_connection_lost.assert_not_called()

    @patch.object(WebSocketClient, "create_timer", autospec=True)
    @patch.object(WebSocketClient, "on_connection_lost", autospec=True)
    def test_on_close_retry(self, mocked_on_connection_lost, mocked_create_timer):
        """Test the callback on connection close when connection should retry."""
        # create the websocket
        self.set_websocket()

        # pre assert
        self.assertFalse(self.client.retry)

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_close(None, None)

        # assert the retry flag is set
        self.assertTrue(self.client.retry)

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            [
                "ERROR:dakara_base.websocket_client:Websocket connection lost",
                "WARNING:dakara_base.websocket_client:Trying to reconnect in 1 s",
            ],
        )

        # assert the different calls
        mocked_create_timer.assert_called_with(
            self.client, self.reconnect_interval, self.client.run
        )
        mocked_create_timer.return_value.start.assert_called_with()
        mocked_on_connection_lost.assert_called_with(self.client)

    @patch.object(WebSocketClient, "receive_dummy", create=True)
    def test_on_message_successful(self, mocked_receive_dummy):
        """Test a normal use of the on message method."""
        event = '{"type": "dummy", "data": "data"}'
        content = "data"

        # call the method
        self.client.on_message(event)

        # assert the dummy method has been called
        mocked_receive_dummy.assert_called_with(content)

    def test_on_message_failed_json(self):
        """Test the on message method when event is not a JSON string."""
        event = "definitely not a JSON string"

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_message(event)

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            [
                "ERROR:dakara_base.websocket_client:"
                "Unexpected message from the server: '{}'".format(event)
            ],
        )

    def test_on_message_failed_type(self):
        """Test the on message method when event has an unknown type."""
        event = '{"type": "dummy", "data": "data"}'

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_message(event)

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            [
                "ERROR:dakara_base.websocket_client:"
                "Event of unknown type received 'dummy'"
            ],
        )

    def test_on_message_failed_no_type(self):
        """Test the on message method when event has no type."""
        event = '{"data": "data"}'

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_message(event)

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            ["ERROR:dakara_base.websocket_client:Event of no type received"],
        )

    def test_on_error_closing(self):
        """Test the callback on error when the program is closing.

        The error should be ignored.
        """
        # close the program
        self.stop.set()

        # call the method
        self.client.on_error(Exception("error message"))

        # assert the list of errors is empty
        self.assertTrue(self.errors.empty())

    def test_on_error_unknown(self):
        """Test the callback on an unknown error.

        The error should be logged only.
        """
        # pre assert
        self.assertFalse(self.stop.is_set())

        class CustomError(Exception):
            pass

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_error(CustomError("error message"))

        # assert the list of errors is empty
        self.assertTrue(self.errors.empty())

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            ["ERROR:dakara_base.websocket_client:Websocket: error message"],
        )

    def test_on_error_authentication(self):
        """Test the callback on error when the authentication is refused."""
        # pre assert
        self.assertFalse(self.stop.is_set())

        # call the method
        self.client.on_error(WebSocketBadStatusException("error %s %s", 0))

        # assert the list of errors is not empty
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, AuthenticationError)

    def test_on_error_network_normal(self):
        """Test the callback on error when the server is unreachable."""
        # pre assert
        self.assertFalse(self.client.retry)
        self.assertFalse(self.stop.is_set())

        # call the method
        self.client.on_error(ConnectionRefusedError("error"))

        # assert the list of errors is not empty
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, NetworkError)

    def test_on_error_network_retry(self):
        """Test the callback on error when the server is unreachable on retry.

        No exception should be raised, the error should be logged only.
        """
        # pre assert
        self.assertFalse(self.stop.is_set())

        # set retry flag on
        self.client.retry = True

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.on_error(ConnectionRefusedError("error"))

        # assert the list of errors is empty
        self.assertTrue(self.errors.empty())

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            ["WARNING:dakara_base.websocket_client:Unable to talk to the server"],
        )

    def test_on_error_endpoint(self):
        """Test the callback on error when the endpoint is invalid."""
        # pre assert
        self.assertFalse(self.stop.is_set())

        # call the method
        self.client.on_error(ConnectionResetError("error"))

        # assert the call
        self.assertFalse(self.errors.empty())
        _, error, _ = self.errors.get()
        self.assertIsInstance(error, ParameterError)

    def test_on_error_closed(self):
        """Test the callback on error when the connection is closed by server."""
        # pre assert
        self.assertFalse(self.stop.is_set())
        self.assertFalse(self.client.retry)

        # call the methods
        self.client.on_error(WebSocketConnectionClosedException("error"))

    def test_send_no_data(self):
        """Test to send message without data."""
        event = '{"type": "my_type"}'
        message_type = "my_type"

        # set the websocket
        self.set_websocket()

        # call the method
        self.client.send(message_type)

        # assert the call
        # we have to parse the strings, as the order in the dictionary is not
        # guaranteed in Python < 3.6
        self.client.websocket.send.assert_called_with(ANY)
        _, args, _ = self.client.websocket.send.mock_calls[0]
        event_sent = args[0]
        self.assertEqual(json.loads(event), json.loads(event_sent))

    def test_send_data_falsy(self):
        """Test to send message with falsy data."""
        event = '{"type": "my_type", "data": 0}'
        message_type = "my_type"

        # set the websocket
        self.set_websocket()

        # call the method
        self.client.send(message_type, 0)

        # assert the call
        # we have to parse the strings, as the order in the dictionary is not
        # guaranteed in Python < 3.6
        self.client.websocket.send.assert_called_with(ANY)
        _, args, _ = self.client.websocket.send.mock_calls[0]
        event_sent = args[0]
        self.assertEqual(json.loads(event), json.loads(event_sent))

    def test_send_data(self):
        """Test to send message with data."""
        event = '{"type": "my_type", "data": [1, 2, 3]}'
        message_type = "my_type"
        data = [1, 2, 3]

        # set the websocket
        self.set_websocket()

        # call the method
        self.client.send(message_type, data)

        # assert the call
        # we have to parse the strings, as the order in the dictionary is not
        # guaranteed in Python < 3.6
        self.client.websocket.send.assert_called_with(ANY)
        _, args, _ = self.client.websocket.send.mock_calls[0]
        event_sent = args[0]
        self.assertEqual(json.loads(event), json.loads(event_sent))

    def test_abort_connected(self):
        """Test to abort the connection."""
        # pre assert
        self.assertFalse(self.client.retry)

        # set the websocket
        self.set_websocket()

        # call the method
        self.client.abort()

        # assert the call
        self.client.websocket.sock.abort.assert_called_with()
        self.assertFalse(self.client.retry)

    def test_abort_disconnected(self):
        """Test to abort the connection when already disconnected."""
        # pre assert
        self.assertFalse(self.client.retry)
        self.assertIsNone(self.client.websocket)

        # call the method
        self.client.abort()

        # assert the call
        self.assertFalse(self.client.retry)

    def test_abort_retry(self):
        """Test to abort the connection when retry is set."""
        # set the retry flag on
        self.client.retry = True

        # call the method
        self.client.abort()

        # assert the call
        self.assertFalse(self.client.retry)

    @patch.object(WebSocketClient, "on_error", autospec=True)
    @patch.object(WebSocketClient, "on_message", autospec=True)
    @patch.object(WebSocketClient, "on_close", autospec=True)
    @patch.object(WebSocketClient, "on_open", autospec=True)
    @patch("dakara_base.websocket_client.WebSocketApp", autospec=True)
    def test_run(
        self,
        mocked_websocket_app_class,
        mocked_on_open,
        mocked_on_close,
        mocked_on_message,
        mocked_on_error,
    ):
        """Test to create and run the connection."""
        # pre assert
        self.assertIsNone(self.client.websocket)

        # call the method
        with self.assertLogs("dakara_base.websocket_client", "DEBUG") as logger:
            self.client.run()

        # assert the effect on logger
        self.assertListEqual(
            logger.output,
            ["DEBUG:dakara_base.websocket_client:Preparing websocket connection"],
        )

        # assert the call
        mocked_websocket_app_class.assert_called_with(
            self.url_ws,
            header=self.header,
            on_open=ANY,
            on_close=ANY,
            on_message=ANY,
            on_error=ANY,
        )
        self.client.websocket.run_forever.assert_called_with()

        # assert that the callback are correctly set
        # since the callback methods are adapted, we cannot check directy if
        # the given method reference is the same as the corresponding instance
        # method
        # so, we check that calling the given method calls the instance method
        websocket = MagicMock()
        _, kwargs = mocked_websocket_app_class.call_args

        kwargs["on_open"](websocket)
        self.client.on_open.assert_called_with(self.client)

        kwargs["on_close"](websocket, None, None)
        self.client.on_close.assert_called_with(self.client, None, None)

        kwargs["on_message"](websocket, "message")
        self.client.on_message.assert_called_with(self.client, "message")

        kwargs["on_error"](websocket, "error")
        self.client.on_error.assert_called_with(self.client, "error")

        # post assert
        # in real world, this test is impossible, since the websocket object
        # has been destroyed by `on_close`
        # we use the fact this callback is not called to check if the
        # object has been created as expected
        # maybe there is a better scenario to test this
        self.assertIsNotNone(self.client.websocket)
