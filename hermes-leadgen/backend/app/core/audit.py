from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.crm import AuditLogEntry


def record_audit(
    db: Session,
    *,
    actor_id: Optional[UUID],
    action: str,
    object_type: str = "",
    object_id: str = "",
    detail: str = "",
    ip_address: str = "",
) -> AuditLogEntry:
    entry = AuditLogEntry(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry
