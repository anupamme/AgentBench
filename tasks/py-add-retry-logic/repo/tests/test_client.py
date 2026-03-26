from unittest.mock import patch, MagicMock
import urllib.error
import pytest
from client import fetch_data


def test_fetch_success_first_try():
    mock_response = MagicMock()
    mock_response.read.return_value = b"hello"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_response):
        result = fetch_data("http://example.com")
    assert result == "hello"


def test_retries_on_failure():
    """Should succeed on the third attempt after two failures."""
    call_count = 0

    def fake_urlopen(url):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise urllib.error.URLError("temporary failure")
        mock = MagicMock()
        mock.read.return_value = b"ok"
        mock.__enter__ = lambda s: s
        mock.__exit__ = MagicMock(return_value=False)
        return mock

    with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         patch("time.sleep"):
        result = fetch_data("http://example.com")
    assert result == "ok"
    assert call_count == 3


def test_raises_after_max_retries():
    """Should raise after 3 failed attempts."""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")), \
         patch("time.sleep"):
        with pytest.raises(urllib.error.URLError):
            fetch_data("http://example.com")
