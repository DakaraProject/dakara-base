import pytest

from dakara_base.utils import URLParameterError, create_url, strtobool, truncate_message


class TestTruncateMessage:
    def test_small_message(self):
        """Test a small message is completelly displayed."""
        message = "few characters"
        message_displayed = truncate_message(message, limit=50)

        assert len(message_displayed) <= 50
        assert message_displayed == "few characters"

    def test_long_message(self):
        """Test a long message is cut."""
        message = "few characters"
        message_displayed = truncate_message(message, limit=5)

        assert len(message_displayed) == 5
        assert message_displayed == "fe..."

    def test_too_short_limit(self):
        """Test a too short limit.

        This case is marginal.
        """
        message = "few characters"

        with pytest.raises(AssertionError, match="Limit too short"):
            truncate_message(message, limit=2)


class TestCreateUrl:
    """Test the URL creator helper."""

    def test_url(self):
        """Test to create URL directly with provided URL."""
        url = create_url(url="http://www.example.com", host="www.other.com")
        assert url == "http://www.example.com"

    def test_url_path(self):
        """Test to create URL directly with provided URL and path."""
        url = create_url(url="http://www.example.com", path="path/to/resource")
        assert url == "http://www.example.com/path/to/resource"

    def test_host(self):
        """Test to create URL with provided host."""
        url = create_url(host="www.example.com", scheme_no_ssl="http")
        assert url == "http://www.example.com"

    def test_host_ssl(self):
        """Test to create URL with provided host and SSL security."""
        url = create_url(host="www.example.com", ssl=True, scheme_ssl="https")
        assert url == "https://www.example.com"

    def test_host_port(self):
        """Test to create URL with provided host and port."""
        url = create_url(host="www.example.com", port=8000, scheme_no_ssl="http")
        assert url == "http://www.example.com:8000"

    def test_host_path(self):
        """Test to create URL with provided host and path."""
        url = create_url(
            host="www.example.com", path="path/to/resource", scheme_no_ssl="http"
        )
        assert url == "http://www.example.com/path/to/resource"

    def test_address_host(self):
        """Test to create URL with provided address containing host."""
        url = create_url(address="www.example.com", scheme_no_ssl="http")
        assert url == "http://www.example.com"

    def test_address_host_port(self):
        """Test to create URL with provided address containing host and port."""
        url = create_url(address="www.example.com:8000", scheme_no_ssl="http")
        assert url == "http://www.example.com:8000"

    def test_nothing(self):
        """Test to create URL when nothing is provided."""
        with pytest.raises(URLParameterError):
            create_url()

    def test_invalid_furl(self, mocker):
        """Test to create URL with invalid arguments for furl."""
        mocker.patch(
            "dakara_base.utils.furl", side_effect=ValueError("error"), autospec=True
        )
        with pytest.raises(URLParameterError):
            create_url(host="www.example.com", scheme_no_ssl="http")


class TestStrtobool:
    def test_y(self):
        """Test True representations"""
        for uinput in ("y", "yes", "Y", "YES"):
            assert strtobool(uinput)

    def test_n(self):
        """Test False representations"""
        for uinput in ("n", "no", "N", "NO"):
            assert not strtobool(uinput, default=True)

    def test_default(self):
        """Test default value"""
        assert strtobool("not a known input", default=True)
        assert not strtobool("not a known input", default=False)
