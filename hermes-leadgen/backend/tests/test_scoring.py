import json

from app.models.lead import Lead
from app.models.scoring import ScoreEvidence
from app.services.scoring_engine import score_lead, seed_default_scoring_rules


def test_seed_default_rules_totals_100_points(db_session):
    seed_default_scoring_rules(db_session)
    db_session.commit()
    from app.models.scoring import ScoringRule
    rules = db_session.query(ScoringRule).all()
    assert sum(r.max_points for r in rules) == 100


def test_strong_lead_scores_hot(db_session):
    lead = Lead(
        company_name="Pixel & Pine Automation Agency",
        website="https://pixelandpine.example.com",
        description=(
            "We build custom automations and chatbots for e-commerce clients and manage "
            "support over Slack and Telegram, handling repetitive onboarding and customer support tickets."
        ),
        public_email="team@pixelandpine.example.com",
        contact_page_url="https://pixelandpine.example.com/contact",
        estimated_company_size="2-10",
    )
    db_session.add(lead)
    db_session.commit()

    scored = score_lead(db_session, lead)
    db_session.commit()

    assert scored.score >= 75
    assert scored.tier == "hot"
    evidence = db_session.query(ScoreEvidence).filter_by(lead_id=lead.id).all()
    assert len(evidence) == 8
    explanation = json.loads(scored.score_explanation)
    assert all("why" in e for e in explanation)


def test_weak_lead_scores_cold(db_session):
    lead = Lead(company_name="Generic Corp", estimated_company_size="5000+")
    db_session.add(lead)
    db_session.commit()

    scored = score_lead(db_session, lead)
    db_session.commit()

    assert scored.tier == "cold"
    assert scored.score < 50


def test_disabling_a_rule_removes_its_points(db_session):
    seed_default_scoring_rules(db_session)
    from app.models.scoring import ScoringRule
    rule = db_session.query(ScoringRule).filter_by(key="public_contact_method").first()
    rule.is_enabled = False
    db_session.commit()

    lead = Lead(company_name="Contact Only Co", public_email="hi@example.com")
    db_session.add(lead)
    db_session.commit()

    scored = score_lead(db_session, lead)
    evidence_keys = {e.rule_key for e in db_session.query(ScoreEvidence).filter_by(lead_id=lead.id).all()}
    assert "public_contact_method" not in evidence_keys
