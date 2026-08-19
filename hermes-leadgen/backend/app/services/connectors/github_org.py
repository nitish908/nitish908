"""GitHub public-organization connector — uses GitHub's official REST API only
(no scraping). Works unauthenticated at a low rate limit, or with
GITHUB_TOKEN configured for a higher limit.
"""
from __future__ import annotations

import requests

from app.core.config import get_settings
from app.core.ssrf_guard import assert_safe_url
from app.services.connectors.base import Connector, DiscoveredLead

GITHUB_API_BASE = "https://api.github.com"


class GitHubOrgConnector(Connector):
    source_type = "github_org"
    display_name = "GitHub public organization"

    def __init__(self, org_login: str):
        self.org_login = org_login
        self._settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.org_login)

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "hermes-leadgen"}
        if self._settings.github_token:
            headers["Authorization"] = f"Bearer {self._settings.github_token}"
        return headers

    def discover(self, *, limit: int) -> list[DiscoveredLead]:
        url = f"{GITHUB_API_BASE}/orgs/{self.org_login}"
        assert_safe_url(url)
        resp = requests.get(url, headers=self._headers(), timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        website = data.get("blog") or None
        if website and not website.startswith("http"):
            website = f"https://{website}"
        lead = DiscoveredLead(
            company_name=data.get("name") or self.org_login,
            website=website,
            description=data.get("description") or None,
            country=data.get("location") or None,
            public_email=data.get("email") or None,
            source_name="github_org",
            source_url=data.get("html_url"),
            extra_signals=["Publishes open-source software on GitHub"],
        )
        return [lead][:limit]
