"""robots.txt compliance for the research pipeline.

Every fetch must pass both the SSRF guard and this robots.txt check before
any page content is read. Results are cached per-domain for the life of the
process to avoid re-fetching robots.txt for every page.
"""
from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from app.core.ssrf_guard import check_url

USER_AGENT = "HermesLeadgenResearchBot/0.1 (+https://example.com/bot)"

_robots_cache: dict[str, RobotFileParser] = {}


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def _get_parser(url: str, *, timeout: int) -> RobotFileParser:
    robots_url = _robots_url(url)
    if robots_url in _robots_cache:
        return _robots_cache[robots_url]

    parser = RobotFileParser()
    parser.set_url(robots_url)

    ssrf_result = check_url(robots_url)
    if not ssrf_result.allowed:
        # Fail closed for the robots fetch itself; treat as "disallow all"
        # so we never fetch pages we couldn't validate the policy for.
        parser.parse(["User-agent: *", "Disallow: /"])
        _robots_cache[robots_url] = parser
        return parser

    try:
        resp = requests.get(robots_url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if resp.status_code >= 400:
            # No robots.txt (or inaccessible) is treated as "allow" per convention.
            parser.parse(["User-agent: *", "Allow: /"])
        else:
            parser.parse(resp.text.splitlines())
    except requests.RequestException:
        # Network failure fetching robots.txt: fail closed.
        parser.parse(["User-agent: *", "Disallow: /"])

    _robots_cache[robots_url] = parser
    return parser


def is_allowed(url: str, *, timeout: int = 10) -> bool:
    parser = _get_parser(url, timeout=timeout)
    return parser.can_fetch(USER_AGENT, url)
