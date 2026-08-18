from app.models.lead import Lead
from app.services.dedup import find_existing_duplicate, normalize_company_name, normalize_domain


def test_normalize_domain_strips_scheme_and_www():
    assert normalize_domain("https://www.Example.com/about") == "example.com"
    assert normalize_domain("example.com") == "example.com"
    assert normalize_domain(None) is None
    assert normalize_domain("") is None


def test_normalize_company_name():
    assert normalize_company_name("Acme, Inc.") == "acme inc"


def test_find_existing_duplicate_by_domain(db_session):
    db_session.add(Lead(company_name="Acme Inc", website="https://acme.com", domain_key="acme.com"))
    db_session.commit()

    dup = find_existing_duplicate(db_session, company_name="Something Else", website="https://www.acme.com/contact")
    assert dup is not None
    assert dup.company_name == "Acme Inc"


def test_find_existing_duplicate_by_name_when_no_website(db_session):
    db_session.add(Lead(company_name="Acme Inc"))
    db_session.commit()

    dup = find_existing_duplicate(db_session, company_name="acme, inc.", website=None)
    assert dup is not None


def test_no_duplicate_for_distinct_company(db_session):
    db_session.add(Lead(company_name="Acme Inc", website="https://acme.com", domain_key="acme.com"))
    db_session.commit()

    dup = find_existing_duplicate(db_session, company_name="Beta LLC", website="https://beta.com")
    assert dup is None
