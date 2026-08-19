import csv
import io
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_audit
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.models.crm import LeadActivity, LeadNote, LeadTask
from app.models.enums import LeadStage
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadNoteCreate, LeadOut, LeadTaskCreate, LeadUpdate
from app.services.csv_import import import_leads_from_csv
from app.services.dedup import find_existing_duplicate, normalize_domain
from app.services.scoring_engine import score_lead
from app.services.suppression import is_suppressed

router = APIRouter(prefix="/api/leads", tags=["leads"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[LeadOut])
def list_leads(
    stage: Optional[str] = None,
    tier: Optional[str] = None,
    industry: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Lead)
    if stage:
        stmt = stmt.where(Lead.stage == stage)
    if tier:
        stmt = stmt.where(Lead.tier == tier)
    if industry:
        stmt = stmt.where(Lead.industry == industry)
    if q:
        stmt = stmt.where(Lead.company_name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Lead.score.desc(), Lead.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if is_suppressed(db, email=payload.public_email, website=payload.website):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This contact/domain is on the suppression list")
    if find_existing_duplicate(db, company_name=payload.company_name, website=payload.website):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A lead for this company/domain already exists")

    lead = Lead(**payload.model_dump(), domain_key=normalize_domain(payload.website))
    db.add(lead)
    db.flush()
    record_audit(db, actor_id=user.id, action="lead_created", object_type="lead", object_id=str(lead.id))
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: UUID, payload: LeadUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    data = payload.model_dump(exclude_unset=True)
    old_stage = lead.stage
    for field, value in data.items():
        setattr(lead, field, value)

    if "stage" in data and data["stage"] != old_stage:
        db.add(LeadActivity(lead_id=lead.id, actor_id=user.id, activity_type="stage_change", detail=f"{old_stage} -> {data['stage']}"))
        if data["stage"] == LeadStage.DO_NOT_CONTACT.value:
            lead.is_suppressed = True

    record_audit(db, actor_id=user.id, action="lead_updated", object_type="lead", object_id=str(lead.id), detail=str(data))
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/score", response_model=LeadOut)
def rescore_lead(lead_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = score_lead(db, lead)
    if lead.tier in ("hot", "warm") and lead.stage == LeadStage.DISCOVERED.value:
        lead.stage = LeadStage.QUALIFIED.value
    record_audit(db, actor_id=user.id, action="lead_scored", object_type="lead", object_id=str(lead.id), detail=f"score={lead.score}")
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/import-csv")
def import_csv(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    content = file.file.read()
    result = import_leads_from_csv(db, content, source_name=f"csv_upload:{file.filename}")
    record_audit(
        db, actor_id=user.id, action="csv_import", object_type="lead_source", object_id=file.filename or "",
        detail=f"created={result.created} duplicates={result.duplicates_skipped} suppressed={result.suppressed_skipped}",
    )
    db.commit()
    return {
        "created": result.created,
        "duplicates_skipped": result.duplicates_skipped,
        "suppressed_skipped": result.suppressed_skipped,
        "errors": result.errors,
        "created_lead_ids": result.created_lead_ids,
    }


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    leads = db.scalars(select(Lead).order_by(Lead.score.desc())).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "company_name", "website", "industry", "country", "city", "score", "tier", "stage",
        "public_email", "contact_page_url", "source_name", "source_url", "next_follow_up_at",
    ])
    for lead in leads:
        writer.writerow([
            lead.company_name, lead.website or "", lead.industry or "", lead.country or "", lead.city or "",
            lead.score, lead.tier or "", lead.stage, lead.public_email or "", lead.contact_page_url or "",
            lead.source_name or "", lead.source_url or "", lead.next_follow_up_at or "",
        ])
    buffer.seek(0)
    record_audit(db, actor_id=user.id, action="csv_export", object_type="lead", detail=f"count={len(leads)}")
    db.commit()
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.post("/{lead_id}/notes")
def add_note(lead_id: UUID, payload: LeadNoteCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    note = LeadNote(lead_id=lead_id, author_id=user.id, body=payload.body)
    db.add(note)
    db.add(LeadActivity(lead_id=lead_id, actor_id=user.id, activity_type="note_added", detail=payload.body[:200]))
    db.commit()
    return {"ok": True}


@router.get("/{lead_id}/notes")
def list_notes(lead_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    notes = db.scalars(select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())).all()
    return [{"id": str(n.id), "body": n.body, "author_id": str(n.author_id) if n.author_id else None, "created_at": n.created_at} for n in notes]


@router.get("/{lead_id}/activity")
def list_activity(lead_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    activities = db.scalars(select(LeadActivity).where(LeadActivity.lead_id == lead_id).order_by(LeadActivity.created_at.desc())).all()
    return [{"id": str(a.id), "activity_type": a.activity_type, "detail": a.detail, "created_at": a.created_at} for a in activities]


@router.post("/{lead_id}/tasks")
def add_task(lead_id: UUID, payload: LeadTaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    task = LeadTask(lead_id=lead_id, title=payload.title, due_date=payload.due_date, assignee_id=user.id)
    db.add(task)
    db.commit()
    return {"id": str(task.id)}
