from unittest.mock import Mock, patch

from app.services.research import fetcher, robots


def _reset():
    robots._robots_cache.clear()
    fetcher._domain_request_log.clear()


def _routed_get(page_response: Mock, *, robots_status: int = 404, robots_text: str = ""):
    """robots.py and fetcher.py both do a bare `import requests`, so they share the
    exact same `requests.get` attribute — patching both module namespaces in one
    test clobbers whichever patch is applied second. Route by URL through a single
    patched callable instead."""
    robots_resp = Mock(status_code=robots_status, text=robots_text)

    def _get(url, *args, **kwargs):
        if url.endswith("/robots.txt"):
            return robots_resp
        return page_response

    return patch("app.services.research.fetcher.requests.get", side_effect=_get)


def test_ssrf_blocked_url_is_skipped_before_any_request():
    _reset()
    with patch("app.services.research.fetcher.requests.get") as mock_get:
        result = fetcher.fetch_permitted_page("http://169.254.169.254/latest/meta-data/")
        assert result.allowed is False
        assert "SSRF" in result.skip_reason
        mock_get.assert_not_called()


def test_fetch_success_returns_sanitized_text():
    _reset()
    html_resp = Mock(status_code=200, url="https://example.com/about", text="<p>We build things</p>", headers={"Content-Type": "text/html"})
    with _routed_get(html_resp):
        result = fetcher.fetch_permitted_page("https://example.com/about")
    assert result.allowed is True
    assert "We build things" in result.text
    assert result.page_type == "about"


def test_rate_limit_blocks_after_threshold():
    _reset()
    from app.core.config import get_settings
    settings = get_settings()
    html_resp = Mock(status_code=200, url="https://example.com/", text="<p>hi</p>", headers={"Content-Type": "text/html"})
    with _routed_get(html_resp):
        results = [fetcher.fetch_permitted_page("https://example.com/") for _ in range(settings.research_requests_per_domain_per_minute + 2)]
    allowed_count = sum(1 for r in results if r.allowed)
    blocked_count = sum(1 for r in results if not r.allowed and "rate limit" in r.skip_reason)
    assert allowed_count == settings.research_requests_per_domain_per_minute
    assert blocked_count == 2


def test_disallowed_robots_blocks_fetch():
    _reset()
    html_resp = Mock(status_code=200, url="https://example.com/secret", text="<p>should never be seen</p>", headers={"Content-Type": "text/html"})
    with _routed_get(html_resp, robots_status=200, robots_text="User-agent: *\nDisallow: /\n") as mock_get:
        result = fetcher.fetch_permitted_page("https://example.com/secret")
        assert result.allowed is False
        assert "robots.txt" in result.skip_reason
        # Only the robots.txt fetch should have happened; the page itself was never requested.
        assert mock_get.call_count == 1
        assert mock_get.call_args[0][0] == "https://example.com/robots.txt"
