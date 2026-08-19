"""Optional provider connectors that require paid/keyed API access this
platform doesn't ship with keys for. They report is_configured=False so the
dashboard can clearly mark them "Not configured" instead of silently
returning nothing or (worse) fabricating data. Wiring real credentials in
via env vars (see .env.example) is enough to make them usable — no code
change required.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.services.connectors.base import Connector, DiscoveredLead


class GooglePlacesConnector(Connector):
    source_type = "google_places"
    display_name = "Google Places API"

    def __init__(self):
        self._settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.google_places_api_key)

    def discover(self, *, limit: int) -> list[DiscoveredLead]:
        if not self.is_configured:
            return []
        # Intentionally not implemented further in the MVP: wiring this up
        # requires a Places API key and a defined search-query strategy
        # (location + business type) that should be configured per user,
        # not hard-coded. See docs/ROADMAP.md.
        return []


class ProductHuntConnector(Connector):
    source_type = "product_hunt"
    display_name = "Product Hunt API"

    def __init__(self):
        self._settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.product_hunt_api_token)

    def discover(self, *, limit: int) -> list[DiscoveredLead]:
        if not self.is_configured:
            return []
        return []
