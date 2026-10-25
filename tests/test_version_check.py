import logging

from dakara_base.version_check import check_version


def test_check_version_release(caplog):
    """Test to display the version for a release."""
    caplog.set_level(logging.INFO)

    check_version("my project", "0.0.0", "1970-01-01")

    # assert effect on logs
    assert caplog.record_tuples == [
        (
            "dakara_base.version_check",
            logging.INFO,
            "Dakara my project 0.0.0 (1970-01-01)",
        )
    ]


def test_check_version_release_logger(caplog):
    """Test to display the version for a release using a custom logger."""
    caplog.set_level(logging.INFO)
    local_logger = logging.getLogger("my_logger")

    check_version("my project", "0.0.0", "1970-01-01", local_logger)

    # assert effect on logs
    assert caplog.record_tuples == [
        ("my_logger", logging.INFO, "Dakara my project 0.0.0 (1970-01-01)")
    ]


def test_check_version_non_release(caplog):
    """Test to display the version for a non release."""
    caplog.set_level(logging.INFO)

    check_version("my project", "0.1.0-dev", "1970-01-01")

    # assert effect on logs
    assert caplog.record_tuples == [
        (
            "dakara_base.version_check",
            logging.INFO,
            "Dakara my project 0.1.0-dev (1970-01-01)",
        ),
        (
            "dakara_base.version_check",
            logging.WARNING,
            "You are running a dev version, use it at your own risks!",
        ),
    ]
