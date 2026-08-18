from datetime import date, timedelta
from unittest.mock import patch

from app.models.enums import ApprovalStatus
from app.models.lead import Lead
from app.models.outreach import ApprovalRecord, OutreachMessage
from app.workers import tasks


def _patched_session(db_session):
    """The task module opens its own SessionLocal(); point it at the shared
    in-memory test session instead so assertions can see what it wrote.

    The task's own `finally: db.close()` detaches every ORM object that was
    loaded through this shared session, so tests below capture plain UUID
    values *before* running the workflow and re-query fresh objects
    afterward, rather than touching the now-detached Python references.
    """
    return patch("app.workers.tasks.SessionLocal", return_value=db_session)


def test_daily_workflow_scores_and_drafts_hot_leads(db_session):
    lead = Lead(
        company_name="Pixel & Pine Automation Agency",
        website="https://pixelandpine.example.com",
        description="We build custom automations and chatbots, handling customer support tickets and onboarding manually.",
        public_email="team@pixelandpine.example.com",
        contact_page_url="https://pixelandpine.example.com/contact",
    )
    db_session.add(lead)
    db_session.commit()
    lead_id = lead.id

    with _patched_session(db_session), patch("app.workers.tasks.research_lead") as mock_research:
        summary = tasks.run_daily_workflow_sync()

    mock_research.assert_called_once()
    assert summary["leads_scored_this_run"] == 1
    assert summary["drafts_created_this_run"] == 1
    assert summary["errors"] == []

    reloaded_lead = db_session.get(Lead, lead_id)
    assert reloaded_lead.tier == "hot"
    approval = db_session.query(ApprovalRecord).filter_by(lead_id=lead_id).first()
    assert approval is not None
    assert approval.status == ApprovalStatus.PENDING.value


def test_daily_workflow_skips_suppressed_leads(db_session):
    lead = Lead(company_name="Suppressed Co", website="https://suppressed.example.com", is_suppressed=True)
    db_session.add(lead)
    db_session.commit()
    lead_id = lead.id

    with _patched_session(db_session), patch("app.workers.tasks.research_lead") as mock_research:
        summary = tasks.run_daily_workflow_sync()

    mock_research.assert_not_called()
    assert summary["leads_researched_this_run"] == 0
    assert summary["leads_scored_this_run"] == 0
    reloaded_lead = db_session.get(Lead, lead_id)
    assert reloaded_lead.tier is None


def test_daily_workflow_does_not_create_duplicate_drafts(db_session):
    lead = Lead(company_name="Already Drafted Co", website="https://already.example.com", tier="hot", stage="qualified")
    db_session.add(lead)
    db_session.commit()
    lead_id = lead.id

    message = OutreachMessage(lead_id=lead_id, message_type="initial_email", channel="email", body="existing draft")
    db_session.add(message)
    db_session.commit()
    db_session.add(ApprovalRecord(message_id=message.id, lead_id=lead_id, channel="email", status=ApprovalStatus.PENDING.value))
    db_session.commit()

    with _patched_session(db_session), patch("app.workers.tasks.research_lead"):
        summary = tasks.run_daily_workflow_sync()

    assert summary["drafts_created_this_run"] == 0
    count = db_session.query(ApprovalRecord).filter_by(lead_id=lead_id).count()
    assert count == 1


def test_daily_workflow_reports_follow_ups_due(db_session):
    lead = Lead(company_name="Due Today Co", next_follow_up_at=date.today() - timedelta(days=1))
    db_session.add(lead)
    db_session.commit()

    with _patched_session(db_session):
        summary = tasks.run_daily_workflow_sync()

    assert summary["follow_ups_due_count"] == 1


def test_daily_workflow_collects_research_errors_without_aborting(db_session):
    lead = Lead(company_name="Broken Co", website="https://broken.example.com")
    db_session.add(lead)
    db_session.commit()

    with _patched_session(db_session), patch("app.workers.tasks.research_lead", side_effect=RuntimeError("boom")):
        summary = tasks.run_daily_workflow_sync()

    assert any("research failed" in e for e in summary["errors"])
    # scoring still ran despite the research failure
    assert summary["leads_scored_this_run"] == 1
