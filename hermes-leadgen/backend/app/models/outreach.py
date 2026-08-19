from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import ApprovalStatus, MessageChannel, MessageType


class OutreachMessage(UUIDPKMixin, TimestampMixin, Base):
    """A generated (and possibly edited) draft for one lead/message-type pair.
    Never sent without a matching, exact-match ApprovalRecord."""

    __tablename__ = "outreach_messages"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_edited: Mapped[str] = mapped_column(Text, default="")  # human-edited version, if any
    generated_by: Mapped[str] = mapped_column(String(20), default="rule_based")  # rule_based | llm
    cited_company_detail: Mapped[str] = mapped_column(Text, default="")


class ApprovalRecord(UUIDPKMixin, TimestampMixin, Base):
    """The single gate that authorizes sending. A message can only be sent if
    an ApprovalRecord exists whose recipient, channel, content, and scheduled
    time exactly match what is about to be sent."""

    __tablename__ = "approval_records"

    message_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("outreach_messages.id"), nullable=False, index=True)
    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    approved_by_user_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ApprovalStatus.PENDING.value, index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    approved_content_hash: Mapped[str] = mapped_column(String(64), default="")
    scheduled_send_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
