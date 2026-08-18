from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class ScoringRule(UUIDPKMixin, TimestampMixin, Base):
    """One editable weighted criterion in the 100-point scoring engine."""

    __tablename__ = "scoring_rules"

    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    hot_threshold: Mapped[int] = mapped_column(Integer, default=75)
    warm_threshold: Mapped[int] = mapped_column(Integer, default=50)


class ScoreEvidence(UUIDPKMixin, Base):
    """Evidence recorded for a single rule's points awarded to a single lead."""

    __tablename__ = "score_evidence"

    lead_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
