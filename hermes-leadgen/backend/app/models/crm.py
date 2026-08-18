from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import TaskStatus


class LeadNote(UUIDPKMixin, Base):
    __tablename__ = "lead_notes"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    author_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadActivity(UUIDPKMixin, Base):
    """Append-only activity/status-change history for a lead (stage changes,
    replies recorded, messages approved, etc.)."""

    __tablename__ = "lead_activities"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    actor_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LeadTask(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "lead_tasks"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.OPEN.value)
    assignee_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)


class SuppressionEntry(UUIDPKMixin, Base):
    """Contacts/domains that must never be contacted again (unsubscribe, bounce,
    explicit do-not-contact). Checked before every discovery/draft/send step."""

    __tablename__ = "suppression_entries"

    value: Mapped[str] = mapped_column(String(400), nullable=False, index=True)  # email or domain
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)  # email | domain
    reason: Mapped[str] = mapped_column(String(200), default="")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLogEntry(UUIDPKMixin, Base):
    """Security- and compliance-relevant actions: logins, credential changes,
    approvals, sends, exports, deletions, role changes."""

    __tablename__ = "audit_log_entries"

    actor_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_type: Mapped[str] = mapped_column(String(60), default="")
    object_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
