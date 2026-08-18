from app.models.enums import MessageType
from app.models.lead import Lead
from app.models.research import ResearchFinding
from app.services.outreach.generator import generate_draft


def test_generate_draft_pulls_from_research_findings(db_session, monkeypatch):
    monkeypatch.setenv("SENDER_NAME", "Jane Doe")
    monkeypatch.setenv("SENDER_CONTACT_EMAIL", "jane@example.com")
    from app.core.config import get_settings
    get_settings.cache_clear()

    lead = Lead(company_name="Acme Inc", website="https://acme.com", contact_page_url="https://acme.com/contact")
    db_session.add(lead)
    db_session.commit()
    db_session.add(ResearchFinding(lead_id=lead.id, finding_type="summary", content="Acme builds widgets.", confidence="verified", citation_url="https://acme.com/about"))
    db_session.add(ResearchFinding(lead_id=lead.id, finding_type="pain_point", content="Manual order intake.", confidence="assumption", citation_url="https://acme.com/about"))
    db_session.add(ResearchFinding(lead_id=lead.id, finding_type="use_case", content="Automate order intake via Telegram.", confidence="assumption", citation_url="https://acme.com/about"))
    db_session.commit()

    message = generate_draft(db_session, lead, MessageType.INITIAL_EMAIL.value)
    db_session.commit()

    assert message.channel == "email"
    assert "Acme builds widgets" in message.body
    assert "Manual order intake" in message.body
    assert "Automate order intake via Telegram" in message.body
    assert message.cited_company_detail == "Acme builds widgets."
    get_settings.cache_clear()


def test_generate_draft_falls_back_to_lead_fields_without_research(db_session):
    lead = Lead(company_name="Beta LLC", description="Beta does consulting.", outreach_angle="automate scheduling")
    db_session.add(lead)
    db_session.commit()

    message = generate_draft(db_session, lead, MessageType.LINKEDIN_DRAFT.value)
    assert "Beta does consulting" in message.body
    assert message.channel == "linkedin_manual"


def test_generate_draft_unknown_type_raises(db_session):
    lead = Lead(company_name="Gamma Co")
    db_session.add(lead)
    db_session.commit()
    import pytest
    with pytest.raises(ValueError):
        generate_draft(db_session, lead, "not_a_real_type")
