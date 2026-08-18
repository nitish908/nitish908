from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import SourceType


class LeadSource(UUIDPKMixin, TimestampMixin, Base):
    """A configured connector instance (e.g. 'CSV upload 2026-08-18', 'GitHub org: acme-inc')."""

    __tablename__ = "lead_sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # Non-secret configuration only (e.g. {"org": "acme-inc"}); secrets live in SourceCredential.
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str] = mapped_column(Text, default="")


class SourceCredential(UUIDPKMixin, TimestampMixin, Base):
    """Encrypted API credentials for a lead source, decoupled from LeadSource so
    credential rows can be rotated/audited without touching source config."""

    __tablename__ = "source_credentials"

    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    credential_name: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
