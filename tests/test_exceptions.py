import logging

import pytest

from dakara_base.exceptions import (
    DakaraError,
    DakaraHandledError,
    generate_exception_handler,
    handle_all_exceptions,
)


class TestGenerateExceptionHandle:
    def test_handler(self):
        """Test to generate and use an exception handler"""

        class MyError(Exception):
            pass

        handler = generate_exception_handler(MyError, "handler message")

        # assert the error has 2 parent classes
        with pytest.raises(MyError, match=r"initial message\nhandler message"):
            with handler():
                raise MyError("initial message")

        with pytest.raises(
            DakaraHandledError, match=r"initial message\nhandler message"
        ):
            with handler():
                raise MyError("initial message")


class TestHandleAllExceptions:
    def test_normal_exit(self):
        """Test a normal exit."""
        with handle_all_exceptions("url") as exit_value:
            pass

        assert exit_value.value == 0

    def test_keyboard_interrupt(self, caplog):
        """Test a Ctrl+C exit."""
        caplog.set_level(logging.INFO)
        with handle_all_exceptions("url") as exit_value:
            raise KeyboardInterrupt

        assert exit_value.value == 255
        assert caplog.record_tuples == [
            ("dakara_base.exceptions", logging.INFO, "Quit by user")
        ]

    def test_keyboard_interrupt_already_caught(self):
        """Test a Ctrl+C exit that is caught by the executed block."""
        with handle_all_exceptions("url") as exit_value:
            try:
                raise KeyboardInterrupt

            except KeyboardInterrupt:
                pass

        assert exit_value.value == 0

    def test_known_error(self, caplog):
        """Test a known error exit."""
        with handle_all_exceptions("url") as exit_value:
            raise DakaraError("error")

        assert exit_value.value == 1
        assert caplog.record_tuples == [
            ("dakara_base.exceptions", logging.CRITICAL, "error")
        ]

    def test_known_error_debug(self):
        """Test a known error exit in debug mode."""
        with pytest.raises(DakaraError, match="error"):
            with handle_all_exceptions("url", debug=True) as exit_value:
                raise DakaraError("error")

        assert exit_value.value == 1

    def test_unknown_error(self, caplog):
        """Test an unknown error exit."""
        with handle_all_exceptions("url") as exit_value:
            raise Exception("error")

        assert exit_value.value == 2
        assert caplog.record_tuples == [
            ("dakara_base.exceptions", logging.ERROR, "Unexpected error: error"),
            (
                "dakara_base.exceptions",
                logging.CRITICAL,
                "Please fill a bug report at 'url'",
            ),
        ]

    def test_unknown_error_debug(self):
        """Test an unknown error exit in debug mode."""
        with pytest.raises(Exception, match="error"):
            with handle_all_exceptions("url", debug=True) as exit_value:
                raise Exception("error")

        assert exit_value.value == 2
