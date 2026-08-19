from unittest.mock import patch

from app.models.lead import Lead
from app.models.research import ResearchFinding, ResearchPageFetch
from app.services.research.analyzer import AnalysisResult
from app.services.research.fetcher import FetchResult
from app.services.research.orchestrator import research_lead


def test_research_lead_persists_findings_and_page_fetches(db_session):
    lead = Lead(company_name="Acme Inc", website="https://acme.example.com")
    db_session.add(lead)
    db_session.commit()

    fake_fetch = FetchResult(
        url="https://acme.example.com", final_url="https://acme.example.com", http_status=200,
        text="We build things and handle support manually.", page_type="home", allowed=True,
    )
    fake_analysis = AnalysisResult(
        summary="Acme builds things.",
        pain_point="Manual support replies.",
        use_case="Automate first-line support via Telegram.",
        service_package="Starter Setup",
        field_confidence={"summary": "verified", "pain_point": "assumption", "use_case": "assumption", "service_package": "assumption"},
        generated_by="rule_based",
    )

    with patch("app.services.research.orchestrator.discover_candidate_pages", return_value=["https://acme.example.com"]), \
         patch("app.services.research.orchestrator.fetch_permitted_page", return_value=fake_fetch), \
         patch("app.services.research.orchestrator.analyze_pages", return_value=fake_analysis):
        findings = research_lead(db_session, lead)
    db_session.commit()

    assert len(findings) == 4
    stored_findings = db_session.query(ResearchFinding).filter_by(lead_id=lead.id).all()
    assert len(stored_findings) == 4
    assert any(f.finding_type == "pain_point" and f.confidence == "assumption" for f in stored_findings)

    page_fetches = db_session.query(ResearchPageFetch).filter_by(lead_id=lead.id).all()
    assert len(page_fetches) == 1
    assert page_fetches[0].robots_allowed is True

    assert lead.description == "Acme builds things."
    assert lead.outreach_angle == "Automate first-line support via Telegram."
    assert lead.best_service_package == "Starter Setup"
    assert lead.stage == "researching"


def test_research_lead_skips_without_website(db_session):
    lead = Lead(company_name="No Website Co")
    db_session.add(lead)
    db_session.commit()
    findings = research_lead(db_session, lead)
    assert findings == []
