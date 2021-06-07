from unittest import TestCase
from unittest.mock import patch

from dakara_base.utils import URLParameterError, create_url, truncate_message


class TruncateMessageTestCase(TestCase):
    """Test the message display helper."""

    def test_small_message(self):
        """Test a small message is completelly displayed."""
        message = "few characters"
        message_displayed = truncate_message(message, limit=50)

        self.assertLessEqual(len(message_displayed), 50)
        self.assertEqual(message_displayed, "few characters")

    def test_long_message(self):
        """Test a long message is cut."""
        message = "few characters"
        message_displayed = truncate_message(message, limit=5)

        self.assertLessEqual(len(message_displayed), 5)
        self.assertEqual(message_displayed, "fe...")

    def test_too_short_limit(self):
        """Test a too short limit.

        This case is marginal.
        """
        message = "few characters"

        with self.assertRaises(AssertionError) as error:
            truncate_message(message, limit=2)

        self.assertEqual(str(error.exception), "Limit too short")


class CreateUrlTestCase(TestCase):
    """Test the URL creator helper."""

    def test_url(self):
        """Test to create URL directly with provided URL."""
        url = create_url(url="http://www.example.com", host="www.other.com")
        self.assertEqual(url, "http://www.example.com")

    def test_url_path(self):
        """Test to create URL directly with provided URL and path."""
        url = create_url(url="http://www.example.com", path="path/to/resource")
        self.assertEqual(url, "http://www.example.com/path/to/resource")

    def test_host(self):
        """Test to create URL with provided host."""
        url = create_url(host="www.example.com", scheme_no_ssl="http")
        self.assertEqual(url, "http://www.example.com")

    def test_host_ssl(self):
        """Test to create URL with provided host and SSL security."""
        url = create_url(host="www.example.com", ssl=True, scheme_ssl="https")
        self.assertEqual(url, "https://www.example.com")

    def test_host_port(self):
        """Test to create URL with provided host and port."""
        url = create_url(host="www.example.com", port=8000, scheme_no_ssl="http")
        self.assertEqual(url, "http://www.example.com:8000")

    def test_host_path(self):
        """Test to create URL with provided host and path."""
        url = create_url(
            host="www.example.com", path="path/to/resource", scheme_no_ssl="http"
        )
        self.assertEqual(url, "http://www.example.com/path/to/resource")

    def test_address_host(self):
        """Test to create URL with provided address containing host."""
        url = create_url(address="www.example.com", scheme_no_ssl="http")
        self.assertEqual(url, "http://www.example.com")

    def test_address_host_port(self):
        """Test to create URL with provided address containing host and port."""
        url = create_url(address="www.example.com:8000", scheme_no_ssl="http")
        self.assertEqual(url, "http://www.example.com:8000")

    def test_nothing(self):
        """Test to create URL when nothing is provided."""
        with self.assertRaises(URLParameterError):
            create_url()

    @patch("dakara_base.utils.furl", autospec=True)
    def test_invalid_furl(self, mocked_furl):
        """Test to create URL with invalid arguments for furl."""
        mocked_furl.side_effect = ValueError("error")
        with self.assertRaises(URLParameterError):
            create_url(host="www.example.com", scheme_no_ssl="http")
