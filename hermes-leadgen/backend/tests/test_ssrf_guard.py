import pytest

from app.core.ssrf_guard import assert_safe_url, check_url


@pytest.mark.parametrize("url", [
    "http://localhost/",
    "http://127.0.0.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://172.16.0.1/",
    "http://[::1]/",
    "ftp://example.com/",
    "http://user:pass@example.com/",
    "file:///etc/passwd",
])
def test_blocks_unsafe_urls(url):
    result = check_url(url)
    assert result.allowed is False
    with pytest.raises(ValueError):
        assert_safe_url(url)


@pytest.mark.parametrize("url", [
    "https://example.com/",
    "https://example.com:443/about",
    "http://93.184.216.34/",  # public literal IP (example.com's old address block)
])
def test_allows_safe_public_urls(url):
    result = check_url(url)
    assert result.allowed is True
