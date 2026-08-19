from app.models.crm import SuppressionEntry
from app.models.lead import Lead, LeadFieldAttribution
from app.services.csv_import import import_leads_from_csv

SAMPLE_CSV = (
    "company_name,website,industry,country,city,description,public_email,contact_page_url\n"
    "Acme Inc,https://acme.example.com,Software,US,Austin,A software company,hello@acme.example.com,https://acme.example.com/contact\n"
    "Beta LLC,https://beta.example.com,Agency,US,Denver,A content agency,,https://beta.example.com/contact\n"
)


def test_import_creates_leads_with_attribution(db_session):
    result = import_leads_from_csv(db_session, SAMPLE_CSV.encode(), source_name="csv_upload:test.csv")
    db_session.commit()

    assert result.created == 2
    assert result.duplicates_skipped == 0
    assert result.errors == []

    leads = db_session.query(Lead).all()
    assert {l.company_name for l in leads} == {"Acme Inc", "Beta LLC"}

    acme = next(l for l in leads if l.company_name == "Acme Inc")
    attributions = db_session.query(LeadFieldAttribution).filter_by(lead_id=acme.id).all()
    fields_attributed = {a.field_name for a in attributions}
    assert "website" in fields_attributed
    assert "public_email" in fields_attributed
    assert all(a.source_name == "csv_upload:test.csv" for a in attributions)


def test_import_skips_duplicates_on_second_pass(db_session):
    import_leads_from_csv(db_session, SAMPLE_CSV.encode(), source_name="csv_upload:test.csv")
    db_session.commit()

    result = import_leads_from_csv(db_session, SAMPLE_CSV.encode(), source_name="csv_upload:test2.csv")
    db_session.commit()

    assert result.created == 0
    assert result.duplicates_skipped == 2


def test_import_skips_suppressed_contacts(db_session):
    db_session.add(SuppressionEntry(value="acme.example.com", value_type="domain"))
    db_session.commit()

    result = import_leads_from_csv(db_session, SAMPLE_CSV.encode(), source_name="csv_upload:test.csv")
    db_session.commit()

    assert result.created == 1
    assert result.suppressed_skipped == 1
    remaining = db_session.query(Lead).all()
    assert remaining[0].company_name == "Beta LLC"


def test_import_requires_company_name_column(db_session):
    bad_csv = b"name,website\nAcme,https://acme.example.com\n"
    result = import_leads_from_csv(db_session, bad_csv, source_name="csv_upload:bad.csv")
    assert result.created == 0
    assert result.errors
