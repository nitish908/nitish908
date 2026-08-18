from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.user import User

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_public_settings(_: User = Depends(get_current_user)):
    """Only non-secret operational flags — never returns credentials."""
    s = get_settings()
    return {
        "app_env": s.app_env,
        "outreach_live_send_enabled": s.outreach_live_send_enabled,
        "ai_provider_configured": bool(s.openai_base_url or s.openai_api_key),
        "openai_model": s.openai_model if (s.openai_base_url or s.openai_api_key) else None,
        "sender_name": s.sender_name,
        "sender_company": s.sender_company,
        "sender_contact_email": s.sender_contact_email,
        "lead_data_retention_days": s.lead_data_retention_days,
        "daily_discovery_lead_limit": s.daily_discovery_lead_limit,
    }
