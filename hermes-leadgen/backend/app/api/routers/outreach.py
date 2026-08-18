import csv
import hashlib
import io
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_audit
from app.core.config import get_settings
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.models.enums import ApprovalStatus, MessageType
from app.models.lead import Lead
from app.models.outreach import ApprovalRecord, OutreachMessage
from app.models.user import User
from app.services.outreach.email_provider import get_email_provider
from app.services.outreach.queue import queue_draft

router = APIRouter(prefix="/api/outreach", tags=["outreach"], dependencies=[Depends(verify_csrf)])


def _content_hash(message: OutreachMessage) -> str:
    body = message.body_edited or message.body
    subject = message.subject or ""
    return hashlib.sha256(f"{subject}\n{body}".encode()).hexdigest()


class GenerateDraftRequest(BaseModel):
    message_type: str


@router.post("/leads/{lead_id}/drafts")
def create_draft(lead_id: UUID, payload: GenerateDraftRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.is_suppressed or lead.is_unsubscribed:
        raise HTTPException(status_code=409, detail="This lead is suppressed/unsubscribed; cannot draft outreach")
    if payload.message_type not in {m.value for m in MessageType}:
        raise HTTPException(status_code=400, detail="Unknown message_type")

    message, approval = queue_draft(db, lead, payload.message_type)

    record_audit(db, actor_id=user.id, action="draft_created", object_type="outreach_message", object_id=str(message.id), detail=payload.message_type)
    db.commit()
    db.refresh(message)
    return {
        "message_id": str(message.id), "approval_id": str(approval.id), "subject": message.subject,
        "body": message.body, "channel": message.channel, "cited_company_detail": message.cited_company_detail,
    }


@router.get("/leads/{lead_id}/drafts")
def list_drafts(lead_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    messages = db.scalars(select(OutreachMessage).where(OutreachMessage.lead_id == lead_id).order_by(OutreachMessage.created_at.desc())).all()
    return [
        {
            "id": str(m.id), "message_type": m.message_type, "channel": m.channel, "subject": m.subject,
            "body": m.body, "body_edited": m.body_edited, "cited_company_detail": m.cited_company_detail,
            "created_at": m.created_at,
        }
        for m in messages
    ]


class MessageEdit(BaseModel):
    subject: str | None = None
    body_edited: str | None = None


@router.patch("/messages/{message_id}")
def edit_message(message_id: UUID, payload: MessageEdit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    message = db.get(OutreachMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if payload.subject is not None:
        message.subject = payload.subject
    if payload.body_edited is not None:
        message.body_edited = payload.body_edited
    record_audit(db, actor_id=user.id, action="draft_edited", object_type="outreach_message", object_id=str(message.id))
    db.commit()
    return {"ok": True}


@router.get("/approval-queue")
def approval_queue(status_filter: str = "pending", db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(ApprovalRecord)
    if status_filter and status_filter != "all":
        stmt = stmt.where(ApprovalRecord.status == status_filter)
    stmt = stmt.order_by(ApprovalRecord.created_at.desc())
    records = db.scalars(stmt).all()

    results = []
    for record in records:
        message = db.get(OutreachMessage, record.message_id)
        lead = db.get(Lead, record.lead_id)
        if not message or not lead:
            continue
        results.append({
            "approval_id": str(record.id), "message_id": str(message.id), "lead_id": str(lead.id),
            "company_name": lead.company_name, "score": lead.score, "tier": lead.tier,
            "message_type": message.message_type, "channel": record.channel, "status": record.status,
            "subject": message.subject, "body": message.body_edited or message.body,
            "cited_company_detail": message.cited_company_detail, "scheduled_send_at": record.scheduled_send_at,
        })
    return results


class ApprovalDecision(BaseModel):
    channel: str | None = None
    scheduled_send_at: datetime | None = None


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: UUID, payload: ApprovalDecision, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(ApprovalRecord, approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    lead = db.get(Lead, record.lead_id)
    if lead and (lead.is_suppressed or lead.is_unsubscribed):
        raise HTTPException(status_code=409, detail="This lead is suppressed/unsubscribed; cannot approve outreach")

    message = db.get(OutreachMessage, record.message_id)
    if payload.channel:
        record.channel = payload.channel
    record.approved_content_hash = _content_hash(message)
    record.approved_by_user_id = user.id
    record.approved_at = datetime.now(timezone.utc)
    if payload.scheduled_send_at:
        record.scheduled_send_at = payload.scheduled_send_at
        record.status = ApprovalStatus.SCHEDULED.value
    else:
        record.status = ApprovalStatus.APPROVED.value

    if lead:
        lead.stage = "approved"
        db.add(lead)

    record_audit(db, actor_id=user.id, action="draft_approved", object_type="approval_record", object_id=str(record.id), detail=f"channel={record.channel}")
    db.commit()
    return {"status": record.status}


class RejectRequest(BaseModel):
    reason: str = ""
    prevent_future_contact: bool = False


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: UUID, payload: RejectRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(ApprovalRecord, approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    record.status = ApprovalStatus.REJECTED.value
    record.rejection_reason = payload.reason

    if payload.prevent_future_contact:
        lead = db.get(Lead, record.lead_id)
        if lead:
            lead.is_suppressed = True
            lead.stage = "do_not_contact"
            db.add(lead)

    record_audit(db, actor_id=user.id, action="draft_rejected", object_type="approval_record", object_id=str(record.id), detail=payload.reason)
    db.commit()
    return {"status": record.status}


@router.post("/approvals/{approval_id}/send")
def send_now(approval_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Sends only if: live sending is explicitly enabled, the approval is
    approved/scheduled (never pending/rejected), the message content hasn't
    changed since approval, and the lead isn't suppressed. Otherwise this is
    a deliberate no-op that explains why, per the "never send without exact
    approval match" requirement.
    """
    settings = get_settings()
    if not settings.outreach_live_send_enabled:
        raise HTTPException(
            status_code=400,
            detail="Live sending is disabled in this deployment (OUTREACH_LIVE_SEND_ENABLED=false). "
                   "Use the CSV export in the approval queue to send manually.",
        )

    record = db.get(ApprovalRecord, approval_id)
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")
    if record.status not in (ApprovalStatus.APPROVED.value, ApprovalStatus.SCHEDULED.value):
        raise HTTPException(status_code=409, detail=f"Cannot send a message in status '{record.status}'")

    lead = db.get(Lead, record.lead_id)
    if not lead or lead.is_suppressed or lead.is_unsubscribed:
        raise HTTPException(status_code=409, detail="Lead is suppressed/unsubscribed; refusing to send")

    message = db.get(OutreachMessage, record.message_id)
    if _content_hash(message) != record.approved_content_hash:
        raise HTTPException(status_code=409, detail="Message content changed since approval; re-approve before sending")

    if record.scheduled_send_at and record.scheduled_send_at > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Scheduled send time has not arrived yet")

    if record.channel != "email":
        raise HTTPException(status_code=400, detail=f"Automatic sending is only implemented for the email channel; '{record.channel}' requires manual send")

    if not lead.public_email:
        raise HTTPException(status_code=400, detail="Lead has no public email on file")

    provider = get_email_provider()
    result = provider.send(to_address=lead.public_email, subject=message.subject or "", body=message.body_edited or message.body)
    if not result.ok:
        raise HTTPException(status_code=502, detail=f"Send failed: {result.detail}")

    record.status = ApprovalStatus.SENT.value
    record.sent_at = datetime.now(timezone.utc)
    lead.stage = "contacted"
    lead.last_contacted_at = record.sent_at
    db.add(lead)
    record_audit(db, actor_id=user.id, action="message_sent", object_type="approval_record", object_id=str(record.id), detail=lead.public_email)
    db.commit()
    return {"status": "sent"}


@router.get("/export/csv")
def export_approval_queue_csv(status_filter: str = "all", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ApprovalRecord)
    if status_filter != "all":
        stmt = stmt.where(ApprovalRecord.status == status_filter)
    records = db.scalars(stmt).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["company_name", "public_email", "contact_page_url", "channel", "status", "subject", "body", "cited_company_detail"])
    for record in records:
        message = db.get(OutreachMessage, record.message_id)
        lead = db.get(Lead, record.lead_id)
        if not message or not lead:
            continue
        writer.writerow([
            lead.company_name, lead.public_email or "", lead.contact_page_url or "", record.channel, record.status,
            message.subject or "", message.body_edited or message.body, message.cited_company_detail,
        ])
    buffer.seek(0)
    record_audit(db, actor_id=user.id, action="outreach_csv_export", object_type="approval_record", detail=f"count={len(records)}")
    db.commit()
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outreach_export.csv"},
    )
