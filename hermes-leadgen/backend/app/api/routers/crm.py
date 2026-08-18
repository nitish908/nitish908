from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.core.audit import record_audit
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.models.crm import AuditLogEntry, LeadTask, SuppressionEntry
from app.models.enums import LeadStage
from app.models.lead import Lead
from app.models.user import User
from app.services.suppression import add_to_suppression_list

router = APIRouter(prefix="/api/crm", tags=["crm"], dependencies=[Depends(verify_csrf)])


@router.get("/kanban")
def kanban_board(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    board = {}
    for stage in LeadStage:
        leads = db.scalars(select(Lead).where(Lead.stage == stage.value).order_by(Lead.score.desc()).limit(50)).all()
        board[stage.value] = [{"id": str(l.id), "company_name": l.company_name, "score": l.score, "tier": l.tier} for l in leads]
    return board


@router.get("/follow-ups-due")
def follow_ups_due(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = date.today()
    leads = db.scalars(select(Lead).where(Lead.next_follow_up_at <= today, Lead.is_suppressed.is_(False)).order_by(Lead.next_follow_up_at)).all()
    return [{"id": str(l.id), "company_name": l.company_name, "next_follow_up_at": l.next_follow_up_at, "stage": l.stage} for l in leads]


@router.get("/tasks")
def open_tasks(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    tasks = db.scalars(select(LeadTask).where(LeadTask.status == "open").order_by(LeadTask.due_date)).all()
    return [{"id": str(t.id), "lead_id": str(t.lead_id), "title": t.title, "due_date": t.due_date, "status": t.status} for t in tasks]


class SuppressionCreate(BaseModel):
    value: str
    value_type: str  # email | domain
    reason: str = ""


@router.get("/suppression-list")
def list_suppression(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    entries = db.scalars(select(SuppressionEntry).order_by(SuppressionEntry.added_at.desc())).all()
    return [{"id": str(e.id), "value": e.value, "value_type": e.value_type, "reason": e.reason, "added_at": e.added_at} for e in entries]


@router.post("/suppression-list")
def add_suppression(payload: SuppressionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    entry = add_to_suppression_list(db, value=payload.value, value_type=payload.value_type, reason=payload.reason)
    # also mark any matching existing leads
    matches = db.scalars(select(Lead)).all()
    for lead in matches:
        if (lead.public_email and lead.public_email.lower() == entry.value) or (lead.domain_key and lead.domain_key == entry.value):
            lead.is_suppressed = True
            lead.stage = "do_not_contact"
    record_audit(db, actor_id=user.id, action="suppression_added", object_type="suppression_entry", object_id=str(entry.id), detail=payload.value)
    db.commit()
    return {"id": str(entry.id)}


@router.get("/audit-log")
def audit_log(limit: int = 200, db: Session = Depends(get_db), _: User = Depends(require_owner)):
    entries = db.scalars(select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(limit)).all()
    return [
        {"id": str(e.id), "actor_id": str(e.actor_id) if e.actor_id else None, "action": e.action, "object_type": e.object_type,
         "object_id": e.object_id, "detail": e.detail, "created_at": e.created_at}
        for e in entries
    ]
