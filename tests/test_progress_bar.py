import logging
import sys
from io import StringIO

import progressbar
import pytest
from progressbar.bar import ProgressBarMixinBase

from dakara_base import progress_bar
from tests.utils import get_lines


class TestShrinkablaTextWidget:
    def test_no_shrink(self):
        """Test a not shrinked case."""
        # prepare mock objects
        progress = ProgressBarMixinBase()
        progress.term_width = 80

        # create the widget and update it
        widget = progress_bar.ShrinkableTextWidget("some text here")
        result = widget(progress, {})

        # assert the result
        assert len(result) == 20
        assert result == "some text here      "

    def test_shrink(self):
        """Test a shrinked case."""
        # prepare mock objects
        progress = ProgressBarMixinBase()
        progress.term_width = 40

        # create the widget and update it
        widget = progress_bar.ShrinkableTextWidget("some text here")
        result = widget(progress, {})

        # assert the result
        assert len(result) == 10
        assert result == "some...ere"

    def test_too_short(self):
        """Test a too short case."""
        # create the widget
        with pytest.raises(AssertionError, match="Text too short"):
            progress_bar.ShrinkableTextWidget("some")


class TestProgressBar:
    def test_text(self):
        """Test a bar with text."""
        # call the bar
        file = StringIO()
        for _ in progress_bar.progress_bar(
            range(1), fd=file, term_width=65, text="some text here"
        ):
            pass

        # assert the lines
        assert get_lines(file) == [
            "some text here     0% |    | Elapsed Time: 0:00:00 ETA:  --:--:--",
            "some text here   100% |####| Elapsed Time: 0:00:00 Time:  0:00:00",
        ]

    def test_no_text(self):
        """Test a bar without text."""
        # call the bar
        file = StringIO()
        for _ in progress_bar.progress_bar(range(1), fd=file, term_width=65):
            pass

        # assert the lines
        assert get_lines(file) == [
            "  0% |                     | Elapsed Time: 0:00:00 ETA:  --:--:--",
            "100% |#####################| Elapsed Time: 0:00:00 Time:  0:00:00",
        ]

    def test_stderr_on_no_exception(self, capsys, monkeypatch):
        """Test to check stderr is not kept if no exceptions occur."""
        # enforce progressbar wrapper to use test stderr
        monkeypatch.setattr(progressbar.streams, "original_stderr", sys.stderr)

        sys.stderr.write("error1")
        assert "error1" == capsys.readouterr().err

        # execute the progressbar without exception
        for _ in progress_bar.progress_bar(range(1), term_width=65):
            pass

        sys.stderr.write("error3")
        assert "error3" == capsys.readouterr().err

    def test_no_stderr_on_exception(self, capsys, monkeypatch):
        """Test to check stderr is not kept after an exception."""
        # enforce progressbar wrapper to use test stderr
        monkeypatch.setattr(progressbar.streams, "original_stderr", sys.stderr)

        sys.stderr.write("error1")
        assert "error1" == capsys.readouterr().err

        # execute the progressbar without exception
        try:
            for _ in progress_bar.progress_bar(range(1), term_width=65):
                raise Exception("exception")

        except Exception:
            pass

        sys.stderr.write("error3")
        assert "error3" == capsys.readouterr().err


class TestNullBar:
    def test_text(self, caplog):
        """Test a null bar with text."""
        caplog.set_level(logging.INFO)

        # call the bar
        for _ in progress_bar.null_bar(range(1), text="some text here"):
            pass

        # assert the logs
        assert caplog.record_tuples == [
            ("dakara_base.progress_bar", logging.INFO, "some text here")
        ]

    def test_no_text(self, caplog):
        """Test a null bar without text."""
        caplog.set_level(logging.INFO)

        # call the bar
        for _ in progress_bar.null_bar(range(1)):
            pass

        # assert the logs
        assert caplog.record_tuples == []
