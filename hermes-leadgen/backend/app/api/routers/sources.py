import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_audit
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.models.lead import Lead, LeadFieldAttribution
from app.models.source import LeadSource
from app.models.user import User
from app.services.connectors.github_org import GitHubOrgConnector
from app.services.connectors.registry import provider_status
from app.services.dedup import find_existing_duplicate, normalize_domain
from app.services.suppression import is_suppressed

router = APIRouter(prefix="/api/sources", tags=["sources"], dependencies=[Depends(verify_csrf)])


@router.get("/providers")
def get_providers(_: User = Depends(get_current_user)):
    return provider_status()


class LeadSourceCreate(BaseModel):
    name: str
    source_type: str
    config: dict = {}


@router.get("")
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    sources = db.scalars(select(LeadSource)).all()
    return [
        {"id": str(s.id), "name": s.name, "source_type": s.source_type, "is_enabled": s.is_enabled, "config": json.loads(s.config_json)}
        for s in sources
    ]


@router.post("")
def create_source(payload: LeadSourceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    source = LeadSource(name=payload.name, source_type=payload.source_type, config_json=json.dumps(payload.config))
    db.add(source)
    db.flush()
    record_audit(db, actor_id=user.id, action="source_created", object_type="lead_source", object_id=str(source.id))
    db.commit()
    return {"id": str(source.id)}


@router.post("/{source_id}/run")
def run_source(source_id: UUID, limit: int = 10, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Runs a configured connector's discover() once, deduplicates and
    suppression-filters results, and creates new leads."""
    source = db.get(LeadSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Lead source not found")

    config = json.loads(source.config_json)
    if source.source_type == "github_org":
        org = config.get("org")
        if not org:
            raise HTTPException(status_code=400, detail="GitHub org connector requires config.org")
        connector = GitHubOrgConnector(org)
    else:
        raise HTTPException(status_code=400, detail=f"No runnable connector for source_type '{source.source_type}' yet; use CSV import or manual entry.")

    if not connector.is_configured:
        raise HTTPException(status_code=400, detail=f"{connector.display_name} is not configured")

    discovered = connector.discover(limit=limit)
    created, duplicates, suppressed = 0, 0, 0
    created_ids = []

    for item in discovered:
        if is_suppressed(db, email=item.public_email, website=item.website):
            suppressed += 1
            continue
        if find_existing_duplicate(db, company_name=item.company_name, website=item.website):
            duplicates += 1
            continue
        lead = Lead(
            company_name=item.company_name, website=item.website, industry=item.industry, country=item.country,
            city=item.city, description=item.description, public_email=item.public_email,
            contact_page_url=item.contact_page_url, estimated_company_size=item.estimated_company_size,
            source_id=source.id, source_name=item.source_name, source_url=item.source_url,
            domain_key=normalize_domain(item.website),
            ai_automation_signals_json=json.dumps(item.extra_signals),
        )
        db.add(lead)
        db.flush()
        db.add(LeadFieldAttribution(lead_id=lead.id, field_name="company_name", source_name=item.source_name, source_url=item.source_url))
        created += 1
        created_ids.append(str(lead.id))

    record_audit(db, actor_id=user.id, action="source_run", object_type="lead_source", object_id=str(source.id), detail=f"created={created}")
    db.commit()
    return {"created": created, "duplicates_skipped": duplicates, "suppressed_skipped": suppressed, "created_lead_ids": created_ids}
