"""Progress bar module.

This module regroups utilities for managing a progress bar.

If you use progress bar and logging at the same time, you should call
`dakara_base.config.create_logger` with `wrap=True`.

Two different bars are provided in the module.

The `progress_bar` is a progress bar that can display a descriptive text to
inform which task is going on:

>>> items = ["one", "two", "three"]
>>> for item in progress_bar(items, text="brief description of the task"):
...     pass

The text adapts to the screen width using the `ShrinkableTextWidget` widget.

The `null_bar` is a pseudo progress bar that does not display progress. It was
initialy designed to be used on logs with the same interface as a bar, in order
to not pollute the log file.

>>> items = ["one", "two", "three"]
>>> for item in null_bar(items, text="brief description of the task"):
...     pass

The text is displayed as a log entry.
"""

import logging

import progressbar
from progressbar.widgets import WidgetBase

logger = logging.getLogger(__name__)


class ShrinkableTextWidget(WidgetBase):
    """Widget which size auto-shrinks with terminal width.

    It contains a descriptive text using by default one quarter of the screen
    width, which can be truncated by the middle if it does not fit.

    Args:
        text (str): Text to display on screen.
        ratio (float): Ratio of screen width to use for text.
    """

    def __init__(self, text, ratio=0.25):
        super().__init__()

        assert len(text) > 5, "Text too short"
        self.text = text
        self.ratio = ratio

    def __call__(self, progress, data):
        # set widget width to a fraction of terminal width
        width = int(progress.term_width * self.ratio)

        # truncate text if necessary
        text = self.text
        if len(text) > width:
            half = int(width * 0.5)
            text = text[: half - 2].strip() + "..." + text[-half + 1 :].strip()

        return text.ljust(width)


def progress_bar(iterator, *args, text=None, **kwargs):
    """Generator that gives the default un-muted progress bar for the project.

    It prints an optionnal shrinkable text (if a text is provided), a
    percentage progress, a progress bar and an adaptative ETA.

    Args:
        iterator (iterator): Iterator of items to use the bar with.
        text (str): Text to display describing the current operation.

    Returns:
        generator object: Item handled by the progress bar.
    """
    widgets = []

    # add optional text widget
    if text:
        widgets.extend([ShrinkableTextWidget(text), " "])

    # add other widgets
    widgets.extend(
        [
            progressbar.Percentage(),
            " ",
            progressbar.Bar(),
            " ",
            progressbar.Timer(),
            " ",
            progressbar.AdaptiveETA(),
        ]
    )

    # create progress bar
    with progressbar.ProgressBar(*args, widgets=widgets, **kwargs) as progress:
        for item in progress(iterator):
            yield item


def null_bar(iterator, *args, text=None, **kwargs):
    """Generator that gives the defaylt muted progress bar for the project.

    It only logs the optionnal text.

    Args:
        iterator (iterator): Iterator of items to use the bar with.
        text (str): Text to log describing the current operation.

    Returns:
        generator object: Item handled by the progress bar.
    """
    # log text immediately
    if text:
        logger.info(text)

    # create null progress bar
    with progressbar.NullBar(*args, **kwargs) as progress:
        for item in progress(iterator):
            yield item
