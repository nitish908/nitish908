from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import UUIDPKMixin
from app.models.enums import ResearchConfidence


class ResearchPageFetch(UUIDPKMixin, Base):
    """Record of a single permitted page fetched for a lead, for auditability."""

    __tablename__ = "research_page_fetches"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    page_type: Mapped[str] = mapped_column(String(40), default="")  # home/about/services/contact/product
    http_status: Mapped[str] = mapped_column(String(10), default="")
    robots_allowed: Mapped[bool] = mapped_column(default=True)
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResearchFinding(UUIDPKMixin, Base):
    """A single structured conclusion from company research, with its citation
    and whether it's a verified fact or a marked assumption."""

    __tablename__ = "research_findings"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    finding_type: Mapped[str] = mapped_column(String(40), nullable=False)  # summary/pain_point/use_case/package
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default=ResearchConfidence.ASSUMPTION.value)
    citation_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
