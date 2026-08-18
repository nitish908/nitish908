"""The scheduled daily workflow: discover -> dedupe/suppress (inherent in
discovery) -> research -> score -> draft hot/warm leads -> surface
follow-ups due -> summarize. Every step is wrapped so one failure doesn't
abort the run; failures are collected into the summary's `errors` list,
matching the "Errors and failed jobs" requirement in the daily summary.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.enums import ApprovalStatus, LeadStage, LeadTier
from app.models.lead import Lead
from app.models.outreach import ApprovalRecord
from app.models.source import LeadSource
from app.services.connectors.github_org import GitHubOrgConnector
from app.services.dedup import find_existing_duplicate, normalize_domain
from app.services.outreach.queue import queue_draft
from app.services.reports import compute_daily_summary
from app.services.research.orchestrator import research_lead
from app.services.scoring_engine import score_lead
from app.services.suppression import is_suppressed
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_enabled_sources(db, *, limit: int) -> tuple[int, list[str]]:
    created_total = 0
    errors: list[str] = []
    sources = db.scalars(select(LeadSource).where(LeadSource.is_enabled.is_(True))).all()

    for source in sources:
        if created_total >= limit:
            break
        try:
            config = json.loads(source.config_json)
            if source.source_type == "github_org" and config.get("org"):
                connector = GitHubOrgConnector(config["org"])
            else:
                continue  # no other auto-runnable connector in the MVP

            if not connector.is_configured:
                continue

            for item in connector.discover(limit=limit - created_total):
                if is_suppressed(db, email=item.public_email, website=item.website):
                    continue
                if find_existing_duplicate(db, company_name=item.company_name, website=item.website):
                    continue
                lead = Lead(
                    company_name=item.company_name, website=item.website, industry=item.industry,
                    country=item.country, city=item.city, description=item.description,
                    public_email=item.public_email, contact_page_url=item.contact_page_url,
                    estimated_company_size=item.estimated_company_size, source_id=source.id,
                    source_name=item.source_name, source_url=item.source_url,
                    domain_key=normalize_domain(item.website),
                    ai_automation_signals_json=json.dumps(item.extra_signals),
                )
                db.add(lead)
                created_total += 1
        except Exception as exc:  # noqa: BLE001 - one bad source must not abort the run
            errors.append(f"source '{source.name}' failed: {exc}")

    db.flush()
    return created_total, errors


def run_daily_workflow_sync() -> dict:
    """The actual workflow logic, callable directly (used by the Celery task
    and by tests/the manual 'run now' endpoint) without going through the
    Celery broker."""
    settings = get_settings()
    db = SessionLocal()
    errors: list[str] = []
    researched_count = 0
    scored_count = 0
    drafts_created = 0

    try:
        discovered_count, discovery_errors = _run_enabled_sources(db, limit=settings.daily_discovery_lead_limit)
        errors.extend(discovery_errors)
        db.commit()

        eligible_for_research = db.scalars(
            select(Lead)
            .where(
                Lead.website.is_not(None),
                Lead.is_suppressed.is_(False),
                Lead.stage.in_([LeadStage.DISCOVERED.value, LeadStage.RESEARCHING.value, LeadStage.QUALIFIED.value]),
            )
            .limit(settings.daily_discovery_lead_limit)
        ).all()
        for lead in eligible_for_research:
            try:
                research_lead(db, lead)
                researched_count += 1
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                errors.append(f"research failed for lead {lead.id}: {exc}")

        unscored_or_researched = db.scalars(
            select(Lead).where(Lead.is_suppressed.is_(False), Lead.tier.is_(None))
        ).all()
        for lead in unscored_or_researched:
            try:
                score_lead(db, lead)
                scored_count += 1
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                errors.append(f"scoring failed for lead {lead.id}: {exc}")

        hot_warm_without_draft = db.scalars(
            select(Lead).where(
                Lead.is_suppressed.is_(False),
                Lead.tier.in_([LeadTier.HOT.value, LeadTier.WARM.value]),
                Lead.stage.in_([LeadStage.QUALIFIED.value, LeadStage.DISCOVERED.value, LeadStage.RESEARCHING.value]),
            )
        ).all()
        for lead in hot_warm_without_draft:
            existing = db.scalar(select(ApprovalRecord).where(ApprovalRecord.lead_id == lead.id).limit(1))
            if existing:
                continue
            try:
                queue_draft(db, lead, "initial_email")
                drafts_created += 1
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                errors.append(f"draft generation failed for lead {lead.id}: {exc}")

        follow_ups_due = db.scalars(
            select(Lead).where(Lead.next_follow_up_at.is_not(None), Lead.next_follow_up_at <= date.today(), Lead.is_suppressed.is_(False))
        ).all()

        summary = compute_daily_summary(db)
        summary.update({
            "leads_discovered_this_run": discovered_count,
            "leads_researched_this_run": researched_count,
            "leads_scored_this_run": scored_count,
            "drafts_created_this_run": drafts_created,
            "follow_ups_due_count": len(follow_ups_due),
            "errors": errors,
        })
        logger.info("Daily workflow complete: %s", summary)
        return summary
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_daily_workflow")
def run_daily_workflow() -> dict:
    return run_daily_workflow_sync()
