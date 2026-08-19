"""Configurable 100-point lead scoring engine.

Each rule is stored in the `scoring_rules` table (key, label, max_points,
enabled, thresholds) so weights can be edited from the dashboard without a
deploy. Scoring itself is rule-based / keyword-evidence driven — this repo
ships with no paid classification API dependency, so the MVP works
end-to-end without any AI provider configured. If OPENAI_BASE_URL is set,
callers may additionally route research summarization through the LLM
client (see services/research/analyzer.py); the point-scoring math here
stays deterministic and auditable either way, per the "explain exactly why
the score was assigned" requirement.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LeadTier
from app.models.lead import Lead
from app.models.research import ResearchFinding
from app.models.scoring import ScoreEvidence, ScoringRule

DEFAULT_RULES: list[dict] = [
    {
        "key": "automation_opportunity",
        "label": "Clear automation opportunity",
        "description": "Business processes described suggest a clear fit for an AI agent (repetitive support, scheduling, content ops, customer messaging).",
        "max_points": 25,
    },
    {
        "key": "messaging_platform_usage",
        "label": "Uses Telegram, Discord, Slack, or similar tools",
        "description": "The company already uses a chat platform Hermes Agent can integrate with.",
        "max_points": 15,
    },
    {
        "key": "digital_services",
        "label": "Offers digital services",
        "description": "The company's offering is digital/service-based (agency, SaaS, content, consulting), which tends to be automation-friendly.",
        "max_points": 15,
    },
    {
        "key": "repetitive_workflow",
        "label": "Repetitive content or operational workflow",
        "description": "Evidence of recurring, templated work (content publishing, client onboarding, order processing).",
        "max_points": 15,
    },
    {
        "key": "ai_interest",
        "label": "Evidence of AI interest",
        "description": "The company already mentions AI, automation, or chatbots on its public pages.",
        "max_points": 10,
    },
    {
        "key": "public_contact_method",
        "label": "Public business contact method",
        "description": "A public email address or contact-form page is available.",
        "max_points": 10,
    },
    {
        "key": "smb_fit",
        "label": "Small or medium business fit",
        "description": "Estimated company size suggests an SMB (typical target profile).",
        "max_points": 5,
    },
    {
        "key": "recent_activity",
        "label": "Recent business activity",
        "description": "The lead was discovered from a page/source with recent activity signals.",
        "max_points": 5,
    },
]

_MESSAGING_KEYWORDS = ["telegram", "discord", "slack", "whatsapp business", "chatbot"]
_DIGITAL_SERVICE_KEYWORDS = [
    "agency", "saas", "software", "consulting", "content creation", "marketing agency",
    "e-commerce", "ecommerce", "freelance", "youtube", "creator", "digital services",
]
_REPETITIVE_WORKFLOW_KEYWORDS = [
    "customer support", "onboarding", "scheduling", "content calendar", "order processing",
    "ticketing", "workflow", "repetitive", "manual process", "publishing schedule",
]
_AI_INTEREST_KEYWORDS = ["ai", "artificial intelligence", "automation", "chatbot", "machine learning", "llm", "gpt"]
_AUTOMATION_OPPORTUNITY_KEYWORDS = _REPETITIVE_WORKFLOW_KEYWORDS + ["automate", "automation", "streamline"]
_SMB_SIZE_HINTS = ["1-10", "2-10", "11-50", "1-50", "small", "startup", "solo", "freelancer"]


@dataclass
class RuleResult:
    rule_key: str
    points_awarded: int
    max_points: int
    explanation: str
    source_url: str = ""


def seed_default_scoring_rules(db: Session) -> None:
    existing_keys = {r.key for r in db.scalars(select(ScoringRule))}
    for rule in DEFAULT_RULES:
        if rule["key"] in existing_keys:
            continue
        db.add(ScoringRule(**rule))
    db.flush()


def _corpus_for_lead(db: Session, lead: Lead) -> tuple[str, dict[str, str]]:
    """Builds a lowercased search corpus plus a field->citation-url map so
    evidence explanations can cite the exact source page used."""
    parts: list[str] = []
    citations: dict[str, str] = {}

    for text_field, value in (
        ("description", lead.description),
        ("ai_automation_signals", lead.ai_automation_signals_json),
        ("messaging_platform_signals", lead.messaging_platform_signals_json),
        ("pain_points", lead.pain_points_json),
    ):
        if value:
            parts.append(str(value))

    findings = db.scalars(select(ResearchFinding).where(ResearchFinding.lead_id == lead.id)).all()
    for finding in findings:
        parts.append(finding.content)
        if finding.citation_url:
            citations.setdefault(finding.content[:40], finding.citation_url)

    default_citation = lead.contact_page_url or lead.source_url or lead.website or ""
    return " ".join(parts).lower(), {"default": default_citation}


def _keyword_hit(corpus: str, keywords: list[str]) -> str | None:
    for kw in keywords:
        if kw in corpus:
            return kw
    return None


def evaluate_lead(db: Session, lead: Lead, rules: list[ScoringRule]) -> list[RuleResult]:
    corpus, citations = _corpus_for_lead(db, lead)
    default_citation = citations.get("default", "")
    results: list[RuleResult] = []
    enabled = {r.key: r for r in rules if r.is_enabled}

    def award(key: str, hit: str | None, hit_label: str, no_hit_label: str) -> None:
        rule = enabled.get(key)
        if not rule:
            return
        if hit:
            results.append(
                RuleResult(key, rule.max_points, rule.max_points, f"{hit_label}: found \"{hit}\".", default_citation)
            )
        else:
            results.append(RuleResult(key, 0, rule.max_points, no_hit_label))

    if "automation_opportunity" in enabled:
        hit = _keyword_hit(corpus, _AUTOMATION_OPPORTUNITY_KEYWORDS)
        award(
            "automation_opportunity", hit,
            "Automation opportunity signal",
            "No repetitive-workflow / automation language found on researched pages.",
        )

    if "messaging_platform_usage" in enabled:
        hit = _keyword_hit(corpus, _MESSAGING_KEYWORDS)
        award("messaging_platform_usage", hit, "Messaging platform mentioned", "No Telegram/Discord/Slack usage found.")

    if "digital_services" in enabled:
        hit = _keyword_hit(corpus, _DIGITAL_SERVICE_KEYWORDS)
        award("digital_services", hit, "Digital-service business model", "No digital-service business model detected.")

    if "repetitive_workflow" in enabled:
        hit = _keyword_hit(corpus, _REPETITIVE_WORKFLOW_KEYWORDS)
        award("repetitive_workflow", hit, "Repetitive/operational workflow signal", "No repetitive workflow signal found.")

    if "ai_interest" in enabled:
        hit = _keyword_hit(corpus, _AI_INTEREST_KEYWORDS)
        award("ai_interest", hit, "AI interest signal", "No mention of AI/automation on researched pages.")

    if "public_contact_method" in enabled:
        rule = enabled["public_contact_method"]
        if lead.public_email or lead.contact_page_url:
            method = "public email" if lead.public_email else "contact page"
            results.append(
                RuleResult(
                    "public_contact_method", rule.max_points, rule.max_points,
                    f"Public contact method available ({method}).", lead.contact_page_url or "",
                )
            )
        else:
            results.append(RuleResult("public_contact_method", 0, rule.max_points, "No public email or contact page on file."))

    if "smb_fit" in enabled:
        rule = enabled["smb_fit"]
        size = (lead.estimated_company_size or "").lower()
        if any(hint in size for hint in _SMB_SIZE_HINTS) or not size:
            results.append(
                RuleResult("smb_fit", rule.max_points, rule.max_points, "Estimated size fits the SMB target profile (or unknown, given benefit of the doubt).")
            )
        else:
            results.append(RuleResult("smb_fit", 0, rule.max_points, f"Estimated size '{lead.estimated_company_size}' looks larger than the SMB target profile."))

    if "recent_activity" in enabled:
        rule = enabled["recent_activity"]
        discovered = lead.discovered_at or datetime.now(timezone.utc)
        if discovered.tzinfo is None:
            discovered = discovered.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - discovered).days
        if age_days <= 30:
            results.append(RuleResult("recent_activity", rule.max_points, rule.max_points, f"Discovered {age_days} day(s) ago; treated as recent activity."))
        else:
            results.append(RuleResult("recent_activity", 0, rule.max_points, f"Discovered {age_days} day(s) ago; not counted as recent."))

    return results


def classify_tier(score: int, rules: list[ScoringRule]) -> str:
    hot = min((r.hot_threshold for r in rules), default=75)
    warm = min((r.warm_threshold for r in rules), default=50)
    if score >= hot:
        return LeadTier.HOT.value
    if score >= warm:
        return LeadTier.WARM.value
    return LeadTier.COLD.value


def score_lead(db: Session, lead: Lead) -> Lead:
    rules = list(db.scalars(select(ScoringRule)))
    if not rules:
        seed_default_scoring_rules(db)
        rules = list(db.scalars(select(ScoringRule)))

    db.query(ScoreEvidence).filter(ScoreEvidence.lead_id == lead.id).delete()

    results = evaluate_lead(db, lead, rules)
    total = sum(r.points_awarded for r in results)
    total = max(0, min(100, total))

    for r in results:
        db.add(
            ScoreEvidence(
                lead_id=lead.id,
                rule_key=r.rule_key,
                points_awarded=r.points_awarded,
                max_points=r.max_points,
                explanation=r.explanation,
                source_url=r.source_url,
            )
        )

    lead.score = total
    lead.tier = classify_tier(total, rules)
    lead.score_explanation = json.dumps(
        [{"rule": r.rule_key, "points": r.points_awarded, "max": r.max_points, "why": r.explanation} for r in results]
    )
    db.add(lead)
    db.flush()
    return lead
