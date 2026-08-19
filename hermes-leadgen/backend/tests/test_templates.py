from app.services.outreach.templates import (
    SenderIdentity,
    render_contact_form,
    render_final_follow_up,
    render_follow_up_1,
    render_follow_up_2,
    render_initial_email,
    render_linkedin_draft,
)

SENDER = SenderIdentity(name="Jane Doe", company="Hermes Agent Services", contact_email="jane@example.com")
NO_MANUAL_RESEARCH_PHRASES = ["i noticed", "i checked out", "i've been following", "i researched", "i looked at your"]


def test_initial_email_has_opt_out_and_sender_identity():
    draft = render_initial_email(
        company_name="Acme Inc", detail="Acme builds widgets.", pain_point="Manual order intake.",
        use_case="automate order intake", sender=SENDER, citation_url="https://acme.com",
    )
    assert "unsubscribe" in draft.body.lower()
    assert SENDER.name in draft.body
    assert SENDER.company in draft.body
    assert SENDER.contact_email in draft.body
    assert "Acme Inc" in draft.subject


def test_no_template_claims_manual_research_or_existing_relationship():
    draft = render_initial_email(
        company_name="Acme Inc", detail="Acme builds widgets.", pain_point="Manual order intake.",
        use_case="automate order intake", sender=SENDER, citation_url="https://acme.com",
    )
    lowered = draft.body.lower()
    for phrase in NO_MANUAL_RESEARCH_PHRASES:
        assert phrase not in lowered
    assert "as we discussed" not in lowered
    assert "as a returning customer" not in lowered


def test_cited_detail_is_included_when_present():
    draft = render_initial_email(
        company_name="Acme Inc", detail="Acme runs a Discord community for clients.", pain_point=None,
        use_case=None, sender=SENDER, citation_url="https://acme.com/about",
    )
    assert "Acme runs a Discord community for clients" in draft.body


def test_missing_detail_does_not_fabricate_a_fact():
    draft = render_initial_email(company_name="Acme Inc", detail=None, pain_point=None, use_case=None, sender=SENDER, citation_url="")
    assert "publicly available business information" in draft.body
    assert "Acme Inc" in draft.body


def test_contact_form_has_no_subject_and_is_concise():
    draft = render_contact_form(company_name="Acme Inc", detail="Acme builds widgets.", pain_point=None, use_case=None, sender=SENDER, citation_url="https://acme.com")
    assert draft.subject is None
    assert len(draft.body) < 700


def test_linkedin_draft_has_no_subject():
    draft = render_linkedin_draft(company_name="Acme Inc", detail=None, pain_point=None, use_case=None, sender=SENDER, citation_url="")
    assert draft.subject is None


def test_follow_ups_have_opt_out_except_final_notes_no_further_contact():
    f1 = render_follow_up_1(company_name="Acme Inc", use_case="automate support", sender=SENDER, citation_url="")
    f2 = render_follow_up_2(company_name="Acme Inc", sender=SENDER, citation_url="")
    final = render_final_follow_up(company_name="Acme Inc", sender=SENDER, citation_url="")
    assert "unsubscribe" in f1.body.lower()
    assert "unsubscribe" in f2.body.lower()
    assert "won't be contacted again" in final.body.lower() or "last message" in final.body.lower()
