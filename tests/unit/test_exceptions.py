from unittest import TestCase
from unittest.mock import ANY

from dakara_base.exceptions import (
    DakaraError,
    DakaraHandledError,
    generate_exception_handler,
    handle_all_exceptions,
)


class GenerateExceptionHandleTestCase(TestCase):
    def test_handler(self):
        """Test to generate and use an exception handler"""

        class MyError(Exception):
            pass

        handler = generate_exception_handler(MyError, "handler message")

        with self.assertRaisesRegex(MyError, r"initial message\nhandler message") as cm:
            with handler():
                raise MyError("initial message")

        self.assertIsInstance(cm.exception, MyError)
        self.assertIsInstance(cm.exception, DakaraHandledError)


class HandleAllExceptionsTestCase(TestCase):
    def test_normal_exit(self):
        """Test a normal exit."""
        with handle_all_exceptions("url") as exit_value:
            pass

        self.assertEqual(exit_value.value, 0)

    def test_keyboard_interrupt(self):
        """Test a Ctrl+C exit."""
        with self.assertLogs("dakara_base.exceptions") as logger:
            with handle_all_exceptions("url") as exit_value:
                raise KeyboardInterrupt

        self.assertEqual(exit_value.value, 255)
        self.assertListEqual(
            logger.output, ["INFO:dakara_base.exceptions:Quit by user"]
        )

    def test_keyboard_interrupt_already_caught(self):
        """Test a Ctrl+C exit that is caught by the executed block."""
        with handle_all_exceptions("url") as exit_value:
            try:
                raise KeyboardInterrupt

            except KeyboardInterrupt:
                pass

        self.assertEqual(exit_value.value, 0)

    def test_known_error(self):
        """Test a known error exit."""
        with self.assertLogs("dakara_base.exceptions") as logger:
            with handle_all_exceptions("url") as exit_value:
                raise DakaraError("error")

        self.assertEqual(exit_value.value, 1)
        self.assertListEqual(logger.output, ["CRITICAL:dakara_base.exceptions:error"])

    def test_known_error_debug(self):
        """Test a known error exit in debug mode."""
        with self.assertRaisesRegex(DakaraError, "error"):
            with handle_all_exceptions("url", debug=True) as exit_value:
                raise DakaraError("error")

        self.assertEqual(exit_value.value, 1)

    def test_unknown_error(self):
        """Test an unknown error exit."""
        with self.assertLogs("dakara_base.exceptions") as logger:
            with handle_all_exceptions("url") as exit_value:
                raise Exception("error")

        self.assertEqual(exit_value.value, 2)
        self.assertListEqual(
            logger.output,
            [ANY, "CRITICAL:dakara_base.exceptions:Please fill a bug report at 'url'"],
        )

    def test_unknown_error_debug(self):
        """Test an unknown error exit in debug mode."""
        with self.assertRaisesRegex(Exception, "error"):
            with handle_all_exceptions("url", debug=True) as exit_value:
                raise Exception("error")

        self.assertEqual(exit_value.value, 2)
