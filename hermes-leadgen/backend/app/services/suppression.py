from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.crm import SuppressionEntry
from app.services.dedup import normalize_domain


def is_suppressed(db: Session, *, email: str | None, website: str | None) -> bool:
    values: list[str] = []
    if email:
        values.append(email.strip().lower())
    domain = normalize_domain(website)
    if domain:
        values.append(domain)
    if not values:
        return False
    hit = db.scalar(select(SuppressionEntry).where(SuppressionEntry.value.in_(values)).limit(1))
    return hit is not None


def add_to_suppression_list(db: Session, *, value: str, value_type: str, reason: str = "") -> SuppressionEntry:
    entry = SuppressionEntry(value=value.strip().lower(), value_type=value_type, reason=reason)
    db.add(entry)
    db.flush()
    return entry
