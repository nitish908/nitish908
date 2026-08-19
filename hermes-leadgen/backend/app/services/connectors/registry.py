from app.core.config import get_settings
from app.services.connectors.unconfigured_stubs import GooglePlacesConnector, ProductHuntConnector


def provider_status() -> list[dict]:
    """Status of every optional connector, for the Lead Sources dashboard page."""
    settings = get_settings()
    google = GooglePlacesConnector()
    ph = ProductHuntConnector()
    return [
        {"source_type": "csv_upload", "display_name": "CSV upload", "is_configured": True, "requires": []},
        {"source_type": "manual_entry", "display_name": "Manual entry", "is_configured": True, "requires": []},
        {"source_type": "company_website", "display_name": "Public company website research", "is_configured": True, "requires": []},
        {"source_type": "github_org", "display_name": "GitHub public organization", "is_configured": True, "requires": ["GITHUB_TOKEN (optional, raises rate limit)"]},
        {"source_type": "google_places", "display_name": "Google Places API", "is_configured": google.is_configured, "requires": ["GOOGLE_PLACES_API_KEY"]},
        {"source_type": "product_hunt", "display_name": "Product Hunt API", "is_configured": ph.is_configured, "requires": ["PRODUCT_HUNT_API_TOKEN"]},
    ]
