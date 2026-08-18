"""Duplicate detection for leads.

Primary key for dedup is the normalized website domain (strip scheme,
'www.', path, query, and trailing slash). Falls back to an exact,
case-insensitive company-name match when no website is present.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead


def normalize_domain(website: str | None) -> str | None:
    if not website:
        return None
    candidate = website.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).lower()
    host = re.sub(r"^www\.", "", host)
    host = host.split(":")[0].strip("/")
    return host or None


def normalize_company_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def find_existing_duplicate(db: Session, *, company_name: str, website: str | None) -> Lead | None:
    domain_key = normalize_domain(website)
    if domain_key:
        existing = db.scalar(select(Lead).where(Lead.domain_key == domain_key).limit(1))
        if existing:
            return existing
    normalized_name = normalize_company_name(company_name)
    if not normalized_name:
        return None
    # SQLite/Postgres both support LOWER(); exact normalized match only (no fuzzy match,
    # to avoid false-positive merges of genuinely distinct companies).
    candidates = db.scalars(select(Lead)).all()
    for candidate in candidates:
        if normalize_company_name(candidate.company_name) == normalized_name:
            return candidate
    return None
