from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_audit
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.models.lead import Lead
from app.models.research import ResearchFinding, ResearchPageFetch
from app.models.user import User
from app.services.research.orchestrator import research_lead

router = APIRouter(prefix="/api/leads", tags=["research"], dependencies=[Depends(verify_csrf)])


@router.post("/{lead_id}/research")
def run_research(lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.website:
        raise HTTPException(status_code=400, detail="Lead has no website to research")

    findings = research_lead(db, lead)
    record_audit(db, actor_id=user.id, action="lead_researched", object_type="lead", object_id=str(lead.id), detail=f"findings={len(findings)}")
    db.commit()
    return {"findings_count": len(findings)}


@router.get("/{lead_id}/research")
def get_research(lead_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    findings = db.scalars(select(ResearchFinding).where(ResearchFinding.lead_id == lead_id)).all()
    pages = db.scalars(select(ResearchPageFetch).where(ResearchPageFetch.lead_id == lead_id)).all()
    return {
        "findings": [
            {
                "finding_type": f.finding_type, "content": f.content, "confidence": f.confidence,
                "citation_url": f.citation_url, "created_at": f.created_at,
            }
            for f in findings
        ],
        "pages_fetched": [
            {
                "url": p.url, "page_type": p.page_type, "http_status": p.http_status,
                "robots_allowed": p.robots_allowed, "fetched_at": p.fetched_at,
            }
            for p in pages
        ],
    }
