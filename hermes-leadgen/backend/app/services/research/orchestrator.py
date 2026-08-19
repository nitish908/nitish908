"""Ties the fetcher, sanitizer, and analyzer together into one per-lead
research run, persisting page-fetch records and findings with citations.
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.models.enums import LeadStage
from app.models.lead import Lead, LeadFieldAttribution
from app.models.research import ResearchFinding, ResearchPageFetch
from app.services.research.analyzer import analyze_pages
from app.services.research.fetcher import discover_candidate_pages, fetch_permitted_page


def research_lead(db: Session, lead: Lead) -> list[ResearchFinding]:
    if not lead.website:
        return []

    lead.stage = LeadStage.RESEARCHING.value
    db.add(lead)
    db.flush()

    candidate_urls = discover_candidate_pages(lead.website)
    permitted_pages: list[tuple[str, str, str]] = []

    for url in candidate_urls:
        result = fetch_permitted_page(url)
        db.add(
            ResearchPageFetch(
                lead_id=lead.id,
                url=url,
                page_type=result.page_type,
                http_status=str(result.http_status or ""),
                robots_allowed="robots.txt" not in result.skip_reason,
                content_hash=hashlib.sha256(result.text.encode()).hexdigest() if result.text else "",
            )
        )
        if result.allowed and result.text:
            permitted_pages.append((result.final_url, result.page_type, result.text))

    db.flush()

    analysis = analyze_pages(lead.company_name, permitted_pages)
    findings: list[ResearchFinding] = []
    primary_citation = permitted_pages[0][0] if permitted_pages else (lead.website or "")

    field_map = [
        ("summary", analysis.summary),
        ("pain_point", analysis.pain_point),
        ("use_case", analysis.use_case),
        ("service_package", analysis.service_package),
    ]
    for field_name, content in field_map:
        if not content:
            continue
        finding = ResearchFinding(
            lead_id=lead.id,
            finding_type=field_name,
            content=content,
            confidence=analysis.field_confidence.get(field_name, "assumption"),
            citation_url=primary_citation,
        )
        db.add(finding)
        findings.append(finding)

    if analysis.summary and not lead.description:
        lead.description = analysis.summary
        db.add(LeadFieldAttribution(lead_id=lead.id, field_name="description", source_name="company_website_research", source_url=primary_citation))

    if analysis.pain_point:
        lead.pain_points_json = json.dumps([analysis.pain_point])
    if analysis.use_case and not lead.outreach_angle:
        lead.outreach_angle = analysis.use_case
    if analysis.service_package and not lead.best_service_package:
        lead.best_service_package = analysis.service_package

    db.add(lead)
    db.flush()
    return findings
