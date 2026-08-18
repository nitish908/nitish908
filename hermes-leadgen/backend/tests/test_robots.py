from unittest.mock import Mock, patch

from app.services.research import robots


def _reset_cache():
    robots._robots_cache.clear()


def test_disallowed_path_blocked():
    _reset_cache()
    fake_resp = Mock(status_code=200, text="User-agent: *\nDisallow: /private/\n")
    with patch("app.services.research.robots.requests.get", return_value=fake_resp):
        assert robots.is_allowed("https://example.com/private/secret") is False
        assert robots.is_allowed("https://example.com/public") is True


def test_missing_robots_txt_defaults_to_allow():
    _reset_cache()
    fake_resp = Mock(status_code=404, text="")
    with patch("app.services.research.robots.requests.get", return_value=fake_resp):
        assert robots.is_allowed("https://example.com/anything") is True


def test_network_failure_fails_closed():
    _reset_cache()
    import requests as requests_module
    with patch("app.services.research.robots.requests.get", side_effect=requests_module.RequestException("boom")):
        assert robots.is_allowed("https://example.com/anything") is False


def test_ssrf_blocked_robots_url_fails_closed():
    _reset_cache()
    assert robots.is_allowed("http://169.254.169.254/latest/meta-data/") is False
