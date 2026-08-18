"""Exercises the outreach/approval-queue router functions directly (bypassing
HTTP) against the SQLite test DB, covering the core "never send without an
exact, unedited, human approval match" and "live sending disabled by
default" invariants.
"""
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.api.routers import outreach
from app.models.enums import MessageType
from app.models.lead import Lead
from app.models.outreach import ApprovalRecord
from app.models.user import User


@pytest.fixture()
def owner(db_session):
    user = User(email="owner@example.com", password_hash="x", role="owner")
    db_session.add(user)
    db_session.commit()
    return user


def _make_lead(db_session, **kwargs):
    lead = Lead(company_name="Acme Inc", public_email="hi@acme.com", **kwargs)
    db_session.add(lead)
    db_session.commit()
    return lead


def test_create_draft_adds_pending_approval_record(db_session, owner):
    import uuid

    lead = _make_lead(db_session)
    result = outreach.create_draft(lead.id, outreach.GenerateDraftRequest(message_type=MessageType.INITIAL_EMAIL.value), db=db_session, user=owner)
    db_session.commit()

    record = db_session.get(ApprovalRecord, uuid.UUID(result["approval_id"]))
    assert record.status == "pending"
    assert lead.stage == "draft_ready"


def test_create_draft_refuses_suppressed_lead(db_session, owner):
    lead = _make_lead(db_session, is_suppressed=True)
    with pytest.raises(HTTPException) as exc:
        outreach.create_draft(lead.id, outreach.GenerateDraftRequest(message_type=MessageType.INITIAL_EMAIL.value), db=db_session, user=owner)
    assert exc.value.status_code == 409


def test_send_refused_when_live_sending_disabled(db_session, owner):
    lead = _make_lead(db_session)
    draft_result = outreach.create_draft(lead.id, outreach.GenerateDraftRequest(message_type=MessageType.INITIAL_EMAIL.value), db=db_session, user=owner)
    db_session.commit()
    approval_id = draft_result["approval_id"]

    import uuid
    outreach.approve(uuid.UUID(approval_id), outreach.ApprovalDecision(), db=db_session, user=owner)
    db_session.commit()

    fake_settings = Mock(outreach_live_send_enabled=False)
    with patch("app.api.routers.outreach.get_settings", return_value=fake_settings):
        with pytest.raises(HTTPException) as exc:
            outreach.send_now(uuid.UUID(approval_id), db=db_session, user=owner)
    assert exc.value.status_code == 400
    assert "disabled" in exc.value.detail.lower()


def test_send_refused_if_content_edited_after_approval(db_session, owner):
    lead = _make_lead(db_session)
    draft_result = outreach.create_draft(lead.id, outreach.GenerateDraftRequest(message_type=MessageType.INITIAL_EMAIL.value), db=db_session, user=owner)
    db_session.commit()

    import uuid
    message_id = uuid.UUID(draft_result["message_id"])
    approval_id = uuid.UUID(draft_result["approval_id"])

    outreach.approve(approval_id, outreach.ApprovalDecision(), db=db_session, user=owner)
    db_session.commit()

    # Edit the message body *after* approval -- the content hash no longer matches.
    outreach.edit_message(message_id, outreach.MessageEdit(body_edited="A totally different message body."), db=db_session, user=owner)
    db_session.commit()

    fake_settings = Mock(outreach_live_send_enabled=True)
    with patch("app.api.routers.outreach.get_settings", return_value=fake_settings):
        with pytest.raises(HTTPException) as exc:
            outreach.send_now(approval_id, db=db_session, user=owner)
    assert exc.value.status_code == 409
    assert "changed since approval" in exc.value.detail


def test_send_succeeds_with_matching_approval_and_enabled_flag(db_session, owner):
    lead = _make_lead(db_session)
    draft_result = outreach.create_draft(lead.id, outreach.GenerateDraftRequest(message_type=MessageType.INITIAL_EMAIL.value), db=db_session, user=owner)
    db_session.commit()

    import uuid
    approval_id = uuid.UUID(draft_result["approval_id"])
    outreach.approve(approval_id, outreach.ApprovalDecision(), db=db_session, user=owner)
    db_session.commit()

    from app.services.outreach.email_provider import SendResult

    fake_settings = Mock(outreach_live_send_enabled=True)
    fake_provider = Mock()
    fake_provider.send.return_value = SendResult(ok=True)

    with patch("app.api.routers.outreach.get_settings", return_value=fake_settings), \
         patch("app.api.routers.outreach.get_email_provider", return_value=fake_provider):
        result = outreach.send_now(approval_id, db=db_session, user=owner)

    assert result == {"status": "sent"}
    fake_provider.send.assert_called_once()
    record = db_session.get(ApprovalRecord, approval_id)
    assert record.status == "sent"
    assert lead.stage == "contacted"


def test_reject_with_prevent_future_contact_suppresses_lead(db_session, owner):
    lead = _make_lead(db_session)
    draft_result = outreach.create_draft(lead.id, outreach.GenerateDraftRequest(message_type=MessageType.INITIAL_EMAIL.value), db=db_session, user=owner)
    db_session.commit()

    import uuid
    approval_id = uuid.UUID(draft_result["approval_id"])
    outreach.reject(approval_id, outreach.RejectRequest(reason="not a fit", prevent_future_contact=True), db=db_session, user=owner)
    db_session.commit()

    assert lead.is_suppressed is True
    assert lead.stage == "do_not_contact"
    record = db_session.get(ApprovalRecord, approval_id)
    assert record.status == "rejected"
