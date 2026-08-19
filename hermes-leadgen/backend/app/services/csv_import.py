"""CSV lead import: validates rows, deduplicates against existing leads,
skips suppressed contacts, and stamps per-field source attribution.

Expected columns (extra columns are ignored, missing optional columns are
fine): company_name, website, industry, country, city, description,
public_email, contact_page_url, estimated_company_size, source_url.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.lead import Lead, LeadFieldAttribution
from app.services.dedup import find_existing_duplicate, normalize_domain
from app.services.suppression import is_suppressed

REQUIRED_COLUMNS = {"company_name"}
ATTRIBUTABLE_FIELDS = [
    "website",
    "industry",
    "country",
    "city",
    "description",
    "public_email",
    "contact_page_url",
    "estimated_company_size",
]


@dataclass
class CSVImportResult:
    created: int = 0
    duplicates_skipped: int = 0
    suppressed_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    created_lead_ids: list[str] = field(default_factory=list)


def import_leads_from_csv(db: Session, file_content: bytes, *, source_name: str) -> CSVImportResult:
    result = CSVImportResult()
    try:
        text = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        result.errors.append("File is not valid UTF-8 text")
        return result

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset({c.strip() for c in reader.fieldnames}):
        result.errors.append(f"CSV must include column(s): {', '.join(sorted(REQUIRED_COLUMNS))}")
        return result

    for row_number, raw_row in enumerate(reader, start=2):
        row = {(k or "").strip(): (v or "").strip() for k, v in raw_row.items()}
        company_name = row.get("company_name", "")
        if not company_name:
            result.errors.append(f"Row {row_number}: missing company_name, skipped")
            continue

        website = row.get("website") or None
        public_email = row.get("public_email") or None

        if is_suppressed(db, email=public_email, website=website):
            result.suppressed_skipped += 1
            continue

        if find_existing_duplicate(db, company_name=company_name, website=website):
            result.duplicates_skipped += 1
            continue

        row_source_url = row.get("source_url") or None
        lead = Lead(
            company_name=company_name,
            website=website,
            industry=row.get("industry") or None,
            country=row.get("country") or None,
            city=row.get("city") or None,
            description=row.get("description") or None,
            public_email=public_email,
            contact_page_url=row.get("contact_page_url") or None,
            estimated_company_size=row.get("estimated_company_size") or None,
            source_name=source_name,
            source_url=row_source_url,
            domain_key=normalize_domain(website),
        )
        db.add(lead)
        db.flush()

        for f in ATTRIBUTABLE_FIELDS:
            if row.get(f):
                db.add(
                    LeadFieldAttribution(
                        lead_id=lead.id,
                        field_name=f,
                        source_name=source_name,
                        source_url=row_source_url,
                    )
                )

        result.created += 1
        result.created_lead_ids.append(str(lead.id))

    db.flush()
    return result
