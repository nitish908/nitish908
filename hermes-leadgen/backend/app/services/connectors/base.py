"""Modular lead-source connector architecture.

Every connector implements `discover()` and returns a list of
`DiscoveredLead` records that already carry source attribution. Connectors
must never bypass login pages, CAPTCHAs, robots.txt, API rate limits, or a
service's terms of use — anything that requires that is out of scope for
this platform (see IMPLEMENTATION_PLAN.md).

To add a new source: subclass Connector, implement discover(), and
register it in CONNECTOR_REGISTRY below. Optional providers without
credentials configured must report `is_configured = False` so the UI can
clearly mark them as unavailable instead of silently no-op'ing.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DiscoveredLead:
    company_name: str
    website: str | None = None
    industry: str | None = None
    country: str | None = None
    city: str | None = None
    description: str | None = None
    public_email: str | None = None
    contact_page_url: str | None = None
    estimated_company_size: str | None = None
    source_name: str = ""
    source_url: str | None = None
    extra_signals: list[str] = field(default_factory=list)


class Connector(ABC):
    source_type: str = "base"
    display_name: str = "Base connector"

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True only if all credentials/config this connector needs are present."""

    @abstractmethod
    def discover(self, *, limit: int) -> list[DiscoveredLead]:
        ...
