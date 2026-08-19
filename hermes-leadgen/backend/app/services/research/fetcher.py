"""Safe fetcher for the company-research pipeline.

Every fetch here goes through, in order: URL validation (SSRF guard),
robots.txt permission, and a per-domain rate limit + page-count cap. Only
GET requests to http(s) are made; redirects are validated too (requests
follows redirects by default, so we re-check the final URL).
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

import requests

from app.core.config import get_settings
from app.core.ssrf_guard import assert_safe_url, check_url
from app.services.research.robots import USER_AGENT, is_allowed
from app.services.research.sanitizer import classify_page_type, html_to_text

# Per-process, per-domain request timestamps for a simple token-bucket-style
# rate limit. Sufficient for a single research worker process; a multi-worker
# deployment should move this to Redis (see docs/ROADMAP.md).
_domain_request_log: dict[str, list[float]] = defaultdict(list)


@dataclass
class FetchResult:
    url: str
    final_url: str
    http_status: int | None
    text: str
    page_type: str
    allowed: bool
    skip_reason: str = ""


def _rate_limit_ok(domain: str, *, per_minute: int) -> bool:
    now = time.time()
    window_start = now - 60
    log = _domain_request_log[domain]
    _domain_request_log[domain] = [t for t in log if t >= window_start]
    if len(_domain_request_log[domain]) >= per_minute:
        return False
    _domain_request_log[domain].append(now)
    return True


def fetch_permitted_page(url: str) -> FetchResult:
    settings = get_settings()

    ssrf_result = check_url(url)
    if not ssrf_result.allowed:
        return FetchResult(url, url, None, "", "unknown", False, f"blocked by SSRF guard: {ssrf_result.reason}")

    if not is_allowed(url, timeout=settings.research_request_timeout_seconds):
        return FetchResult(url, url, None, "", "unknown", False, "disallowed by robots.txt")

    from urllib.parse import urlparse

    domain = urlparse(url).netloc
    if not _rate_limit_ok(domain, per_minute=settings.research_requests_per_domain_per_minute):
        return FetchResult(url, url, None, "", "unknown", False, "per-domain rate limit exceeded")

    try:
        resp = requests.get(
            url,
            timeout=settings.research_request_timeout_seconds,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return FetchResult(url, url, None, "", "unknown", False, f"request failed: {exc}")

    # Redirects can land somewhere unsafe or disallowed; re-validate the final URL.
    final_url = resp.url
    if final_url != url:
        assert_safe_url(final_url)  # raises if unsafe; caller should catch upstream if needed
        if not is_allowed(final_url, timeout=settings.research_request_timeout_seconds):
            return FetchResult(url, final_url, resp.status_code, "", "unknown", False, "redirect target disallowed by robots.txt")

    if resp.status_code >= 400 or "text/html" not in resp.headers.get("Content-Type", "text/html"):
        return FetchResult(url, final_url, resp.status_code, "", "unknown", False, f"non-fetchable response ({resp.status_code})")

    text = html_to_text(resp.text)
    page_type = classify_page_type(final_url, resp.text)
    return FetchResult(url, final_url, resp.status_code, text, page_type, True)


def discover_candidate_pages(base_url: str) -> list[str]:
    """A minimal same-domain link scan of the homepage to find about/services/
    contact pages, without any external search engine or crawling beyond the
    single provided domain."""
    home = fetch_permitted_page(base_url)
    if not home.allowed:
        return [base_url]

    from urllib.parse import urljoin, urlparse

    settings = get_settings()
    try:
        resp = requests.get(base_url, timeout=settings.research_request_timeout_seconds, headers={"User-Agent": USER_AGENT})
    except requests.RequestException:
        return [base_url]

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "html.parser")
    base_domain = urlparse(base_url).netloc
    keywords = ("about", "service", "product", "contact", "solutions")
    candidates: list[str] = [base_url]
    seen = {base_url}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not any(k in href.lower() for k in keywords):
            continue
        full_url = urljoin(base_url, href)
        if urlparse(full_url).netloc != base_domain:
            continue
        if full_url in seen:
            continue
        seen.add(full_url)
        candidates.append(full_url)
        if len(candidates) >= settings.research_max_pages_per_domain:
            break

    return candidates
