from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import LeadStage, LeadTier


class Lead(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "leads"

    # --- Public business facts (see data model in the top-level spec) ---
    company_name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Only ever populated from a page the lead's owner can see cited; never generated/guessed.
    public_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    contact_page_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    estimated_company_size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # --- Discovery ---
    source_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("lead_sources.id"), nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # --- Signals (JSON-encoded lists of strings, each carrying implicit source = research citations) ---
    ai_automation_signals_json: Mapped[str] = mapped_column(Text, default="[]")
    messaging_platform_signals_json: Mapped[str] = mapped_column(Text, default="[]")
    pain_points_json: Mapped[str] = mapped_column(Text, default="[]")

    # --- Scoring ---
    score: Mapped[int] = mapped_column(Integer, default=0)
    score_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tier: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # --- Outreach ---
    outreach_angle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    best_service_package: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # --- CRM ---
    stage: Mapped[str] = mapped_column(String(30), default=LeadStage.DISCOVERED.value, index=True)
    owner_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_follow_up_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # --- Compliance ---
    consent_status: Mapped[str] = mapped_column(String(30), default="not_applicable")
    is_suppressed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Dedup ---
    duplicate_of_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    domain_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)


class LeadFieldAttribution(UUIDPKMixin, Base):
    """Per-field source attribution, so every collected fact can be traced to
    exactly where it came from (required by the no-guessing / attribution rule)."""

    __tablename__ = "lead_field_attributions"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
