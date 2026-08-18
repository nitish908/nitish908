"""Shared "generate a draft and put it in the approval queue" step, used by
both the outreach API router and the daily workflow's Celery task so they
can never drift out of sync on what "queued" means."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import ApprovalStatus, LeadStage
from app.models.lead import Lead
from app.models.outreach import ApprovalRecord, OutreachMessage
from app.services.outreach.generator import generate_draft


def queue_draft(db: Session, lead: Lead, message_type: str) -> tuple[OutreachMessage, ApprovalRecord]:
    message = generate_draft(db, lead, message_type)
    approval = ApprovalRecord(message_id=message.id, lead_id=lead.id, channel=message.channel, status=ApprovalStatus.PENDING.value)
    db.add(approval)
    if lead.stage in (LeadStage.DISCOVERED.value, LeadStage.RESEARCHING.value, LeadStage.QUALIFIED.value):
        lead.stage = LeadStage.DRAFT_READY.value
        db.add(lead)
    db.flush()
    return message, approval
