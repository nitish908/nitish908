"""Builds an OutreachMessage draft for a lead + message type from verified
lead/research data. Never invents a company fact: if no research finding or
lead field is available for a slot, the template falls back to a generic
(but still non-committal, non-fabricated) phrase.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import MessageChannel, MessageType
from app.models.lead import Lead
from app.models.outreach import OutreachMessage
from app.models.research import ResearchFinding
from app.services.outreach import templates as tpl

CHANNEL_BY_MESSAGE_TYPE = {
    MessageType.INITIAL_EMAIL.value: MessageChannel.EMAIL.value,
    MessageType.CONTACT_FORM.value: MessageChannel.CONTACT_FORM.value,
    MessageType.LINKEDIN_DRAFT.value: MessageChannel.LINKEDIN_MANUAL.value,
    MessageType.FOLLOW_UP_1.value: MessageChannel.EMAIL.value,
    MessageType.FOLLOW_UP_2.value: MessageChannel.EMAIL.value,
    MessageType.FINAL_FOLLOW_UP.value: MessageChannel.EMAIL.value,
}


def _lead_context(db: Session, lead: Lead) -> dict:
    findings = {f.finding_type: f for f in db.scalars(select(ResearchFinding).where(ResearchFinding.lead_id == lead.id))}

    detail = findings["summary"].content if "summary" in findings else lead.description
    citation_url = findings["summary"].citation_url if "summary" in findings else (lead.contact_page_url or lead.website or "")

    pain_point = findings["pain_point"].content if "pain_point" in findings else None
    if not pain_point:
        try:
            points = json.loads(lead.pain_points_json or "[]")
            pain_point = points[0] if points else None
        except (json.JSONDecodeError, TypeError):
            pain_point = None

    use_case = findings["use_case"].content if "use_case" in findings else lead.outreach_angle

    return {"detail": detail, "citation_url": citation_url, "pain_point": pain_point, "use_case": use_case}


def _sender_identity() -> tpl.SenderIdentity:
    settings = get_settings()
    return tpl.SenderIdentity(
        name=settings.sender_name or "The Hermes Agent Services team",
        company=settings.sender_company,
        contact_email=settings.sender_contact_email or "hello@example.com",
    )


def generate_draft(db: Session, lead: Lead, message_type: str) -> OutreachMessage:
    ctx = _lead_context(db, lead)
    sender = _sender_identity()
    kwargs = dict(company_name=lead.company_name, sender=sender, citation_url=ctx["citation_url"])

    if message_type == MessageType.INITIAL_EMAIL.value:
        content = tpl.render_initial_email(detail=ctx["detail"], pain_point=ctx["pain_point"], use_case=ctx["use_case"], **kwargs)
    elif message_type == MessageType.CONTACT_FORM.value:
        content = tpl.render_contact_form(detail=ctx["detail"], pain_point=ctx["pain_point"], use_case=ctx["use_case"], **kwargs)
    elif message_type == MessageType.LINKEDIN_DRAFT.value:
        content = tpl.render_linkedin_draft(detail=ctx["detail"], pain_point=ctx["pain_point"], use_case=ctx["use_case"], **kwargs)
    elif message_type == MessageType.FOLLOW_UP_1.value:
        content = tpl.render_follow_up_1(use_case=ctx["use_case"], **kwargs)
    elif message_type == MessageType.FOLLOW_UP_2.value:
        content = tpl.render_follow_up_2(**kwargs)
    elif message_type == MessageType.FINAL_FOLLOW_UP.value:
        content = tpl.render_final_follow_up(**kwargs)
    else:
        raise ValueError(f"Unknown message_type: {message_type}")

    message = OutreachMessage(
        lead_id=lead.id,
        message_type=message_type,
        channel=CHANNEL_BY_MESSAGE_TYPE[message_type],
        subject=content.subject,
        body=content.body,
        generated_by="template",
        cited_company_detail=ctx["detail"] or "",
    )
    db.add(message)
    db.flush()
    return message
