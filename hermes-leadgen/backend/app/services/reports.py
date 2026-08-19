"""Metric queries shared by the dashboard API and the daily workflow's
summary step, so both always agree on what a number means."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ApprovalStatus, LeadStage
from app.models.lead import Lead
from app.models.outreach import ApprovalRecord


def compute_overview(db: Session) -> dict:
    total_leads = db.scalar(select(func.count(Lead.id))) or 0
    qualified = db.scalar(select(func.count(Lead.id)).where(Lead.tier.in_(["hot", "warm"]))) or 0
    drafts_awaiting = db.scalar(select(func.count(ApprovalRecord.id)).where(ApprovalRecord.status == ApprovalStatus.PENDING.value)) or 0
    approved = db.scalar(
        select(func.count(ApprovalRecord.id)).where(
            ApprovalRecord.status.in_([ApprovalStatus.APPROVED.value, ApprovalStatus.SCHEDULED.value, ApprovalStatus.SENT.value])
        )
    ) or 0
    replied = db.scalar(select(func.count(Lead.id)).where(Lead.stage == LeadStage.REPLIED.value)) or 0
    demo_booked = db.scalar(select(func.count(Lead.id)).where(Lead.stage == LeadStage.DEMO_BOOKED.value)) or 0
    won = db.scalar(select(func.count(Lead.id)).where(Lead.stage == LeadStage.WON.value)) or 0
    contacted = db.scalar(
        select(func.count(Lead.id)).where(
            Lead.stage.in_([
                LeadStage.CONTACTED.value, LeadStage.REPLIED.value, LeadStage.DEMO_BOOKED.value,
                LeadStage.PROPOSAL_SENT.value, LeadStage.WON.value, LeadStage.LOST.value,
            ])
        )
    ) or 0
    conversion_rate = round((won / contacted) * 100, 1) if contacted else 0.0

    by_industry = dict(db.execute(select(Lead.industry, func.count(Lead.id)).where(Lead.industry.is_not(None)).group_by(Lead.industry)).all())
    by_source = dict(db.execute(select(Lead.source_name, func.count(Lead.id)).where(Lead.source_name.is_not(None)).group_by(Lead.source_name)).all())
    by_tier = dict(db.execute(select(Lead.tier, func.count(Lead.id)).where(Lead.tier.is_not(None)).group_by(Lead.tier)).all())

    return {
        "leads_discovered": total_leads,
        "qualified_leads": qualified,
        "drafts_awaiting_approval": drafts_awaiting,
        "messages_approved": approved,
        "replies": replied,
        "positive_replies": None,
        "meetings_booked": demo_booked,
        "conversion_rate_percent": conversion_rate,
        "estimated_acquisition_cost": None,
        "leads_by_industry": by_industry,
        "leads_by_source": by_source,
        "leads_by_score_tier": by_tier,
    }


def compute_daily_summary(db: Session) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    new_leads = db.scalar(select(func.count(Lead.id)).where(Lead.discovered_at >= since)) or 0
    hot = db.scalar(select(func.count(Lead.id)).where(Lead.tier == "hot", Lead.discovered_at >= since)) or 0
    warm = db.scalar(select(func.count(Lead.id)).where(Lead.tier == "warm", Lead.discovered_at >= since)) or 0
    drafts_awaiting = db.scalar(select(func.count(ApprovalRecord.id)).where(ApprovalRecord.status == ApprovalStatus.PENDING.value)) or 0
    replies_needing_attention = db.scalar(select(func.count(Lead.id)).where(Lead.stage == LeadStage.REPLIED.value)) or 0
    return {
        "since": since.isoformat(),
        "new_leads": new_leads,
        "hot_leads": hot,
        "warm_leads": warm,
        "drafts_awaiting_approval": drafts_awaiting,
        "replies_requiring_attention": replies_needing_attention,
    }
