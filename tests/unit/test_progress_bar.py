import logging
import sys
from contextlib import contextmanager
from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

import progressbar

from dakara_base import progress_bar


class ShrinkablaTextWidgetTestCase(TestCase):
    """Test the widget for shrinkable text."""

    def test_no_shrink(self):
        """Test a not shrinked case."""
        # prepare mock objects
        progress = MagicMock()
        progress.term_width = 80
        data = MagicMock()

        # create the widget and update it
        widget = progress_bar.ShrinkableTextWidget("some text here")
        result = widget(progress, data)

        # assert the result
        self.assertEqual(len(result), 20)
        self.assertEqual(result, "some text here      ")

    def test_shrink(self):
        """Test a not shrinked case."""
        # prepare mock objects
        progress = MagicMock()
        progress.term_width = 40
        data = MagicMock()

        # create the widget and update it
        widget = progress_bar.ShrinkableTextWidget("some text here")
        result = widget(progress, data)

        # assert the result
        self.assertEqual(len(result), 10)
        self.assertEqual(result, "som...here")

    def test_too_short(self):
        """Test a too short case."""
        # create the widget
        with self.assertRaises(AssertionError) as error:
            progress_bar.ShrinkableTextWidget("some")

        # assert the error
        self.assertEqual(str(error.exception), "Text too short")


class ProgressBarTestCase(TestCase):
    """Test the default progress bar."""

    @staticmethod
    def get_lines(file):
        """Get a neat list of printed lines from a dummy file descriptor..

        Args:
            file (io.StringIO): Dummy file descriptor that get the output of
                the progress bar. It must not be closed.

        Returns:
            list of str: List of actually printed lines. Blank lines are removed.
        """
        content = file.getvalue()
        lines = content.replace("\r", "\n").splitlines()
        return [line for line in lines if line.strip()]

    def test_text(self):
        """Test a bar with text."""
        # call the bar
        with StringIO() as file:
            for _ in progress_bar.progress_bar(
                range(1), fd=file, term_width=65, text="some text here"
            ):
                pass

            lines = self.get_lines(file)

        # assert the lines
        self.assertEqual(len(lines), 3)
        self.assertEqual(
            lines,
            [
                "some text here     0% |    | Elapsed Time: 0:00:00 ETA:  --:--:--",
                "some text here   100% |####| Elapsed Time: 0:00:00 Time:  0:00:00",
                "some text here   100% |####| Elapsed Time: 0:00:00 Time:  0:00:00",
            ],
        )

    def test_no_text(self):
        """Test a bar without text."""
        # call the bar
        with StringIO() as file:
            for _ in progress_bar.progress_bar(range(1), fd=file, term_width=65):
                pass

            lines = self.get_lines(file)

        # assert the lines
        self.assertEqual(len(lines), 3)
        self.assertEqual(
            lines,
            [
                "  0% |                     | Elapsed Time: 0:00:00 ETA:  --:--:--",
                "100% |#####################| Elapsed Time: 0:00:00 Time:  0:00:00",
                "100% |#####################| Elapsed Time: 0:00:00 Time:  0:00:00",
            ],
        )

    def test_stderr_on_no_exception(self):
        """Test to check stderr is not captured if no exceptions occur."""
        stderr = StringIO()
        initial_stderr = sys.stderr

        # we patch `sys.stderr` as it is risky to work directly on it, and we
        # patch `progressbar.streams.original_stderr` as it is defined at
        # module loading
        with patch("sys.stderr", stderr), patch(
            "progressbar.streams.original_stderr", stderr
        ), wrap_stderr_progressbar():
            wrapped_stderr = sys.stderr

            # execute the progressbar without exception
            with StringIO() as file:
                for _ in progress_bar.progress_bar(range(1), fd=file, term_width=65):
                    pass

            sys.stderr.write("error")
            after_stderr = sys.stderr

        final_stderr = sys.stderr

        # assert stderrs
        self.assertIs(initial_stderr, final_stderr)
        self.assertIs(wrapped_stderr, after_stderr)
        self.assertIsNot(initial_stderr, wrapped_stderr)
        self.assertIsNot(stderr, wrapped_stderr)
        self.assertIsNot(stderr, initial_stderr)

        # assert stderr value
        value = stderr.getvalue()
        self.assertEqual(value, "error")

    def test_no_stderr_on_exception(self):
        """Test to check stderr does not remain captured after an exception.

        When leaving a progress bar by an exception, it does not call
        `progressbar.streams.stop_capturing` and the stderr is allways
        captured.
        """

        class MyException(Exception):
            pass

        stderr = StringIO()
        initial_stderr = sys.stderr

        with patch("sys.stderr", stderr), patch(
            "progressbar.streams.original_stderr", stderr
        ), wrap_stderr_progressbar():
            wrapped_stderr = sys.stderr

            # execute the progressbar with an exception
            with StringIO() as file:
                try:
                    for _ in progress_bar.progress_bar(
                        range(1), fd=file, term_width=65
                    ):
                        raise MyException("error")

                except MyException:
                    pass

            sys.stderr.write("error")
            after_stderr = sys.stderr

        final_stderr = sys.stderr

        # assert stderrs
        self.assertIs(initial_stderr, final_stderr)
        self.assertIs(wrapped_stderr, after_stderr)
        self.assertIsNot(initial_stderr, wrapped_stderr)
        self.assertIsNot(stderr, wrapped_stderr)
        self.assertIsNot(stderr, initial_stderr)

        # assert stderr value
        value = stderr.getvalue()
        self.assertEqual(value, "error")


@contextmanager
def wrap_stderr_progressbar():
    """Temporary wrap stderr with progressbar tools."""
    try:
        progressbar.streams.wrap_stderr()
        yield None

    finally:
        progressbar.streams.unwrap_stderr()


class NullBarTestCase(TestCase):
    """Test the null progress bar."""

    def setUp(self):
        # create logger similar to the one of the tested module
        self.logger = logging.getLogger("dakara_base.progress_bar")

    def test_text(self):
        """Test a null bar with text."""
        # call the bar
        with self.assertLogs("dakara_base.progress_bar") as logger:
            self.logger.info("start bar")
            for _ in progress_bar.null_bar(range(1), text="some text here"):
                pass

            self.logger.info("end bar")

        # assert the logs
        self.assertListEqual(
            logger.output,
            [
                "INFO:dakara_base.progress_bar:start bar",
                "INFO:dakara_base.progress_bar:some text here",
                "INFO:dakara_base.progress_bar:end bar",
            ],
        )

    def test_no_text(self):
        """Test a null bar without text."""
        # call the bar
        with self.assertLogs("dakara_base.progress_bar") as logger:
            self.logger.info("start bar")
            for _ in progress_bar.null_bar(range(1)):
                pass

            self.logger.info("end bar")

        # assert the logs
        self.assertListEqual(
            logger.output,
            [
                "INFO:dakara_base.progress_bar:start bar",
                "INFO:dakara_base.progress_bar:end bar",
            ],
        )
