from io import StringIO


def get_lines(file: StringIO) -> list[str]:
    """Get a neat list of printed lines from a dummy file descriptor..

    Args:
        file: Dummy file descriptor that get the output of the progress bar. It
            must not be closed.

    Returns:
        List of actually printed lines. Blank lines are removed.
    """
    content = file.getvalue()
    lines = content.replace("\r", "\n").splitlines()
    return [line for line in lines if line.strip()]
