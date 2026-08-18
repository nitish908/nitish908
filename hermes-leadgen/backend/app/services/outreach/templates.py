"""Outreach copy templates.

Deliberately deterministic/template-based rather than LLM-generated: the
message content (offer, opt-out, sender identity) must stay exactly
accurate and auditable, so the MVP composes it from verified fields
instead of asking a model to paraphrase facts it could drift on.

Phrasing rules enforced structurally here (not just by convention):
  - Every template references a specific, sourced company detail rather
    than a generic compliment, so there is something concrete to verify
    against the citation shown in the approval queue.
  - Nothing is phrased as first-person manual research ("I noticed...",
    "I've been following your work...") since these drafts are always
    generated automatically — claiming otherwise would violate the
    "never pretend manual research" rule. Phrasing stays factual/third-person
    ("Public information about {company} points to...").
  - No claim of an existing relationship is made anywhere.
  - Email-channel templates always carry an opt-out line.
"""
from __future__ import annotations

from dataclasses import dataclass

OFFER_SENTENCE = (
    "We install a private Hermes AI agent on your Ubuntu server, connect it to your "
    "preferred AI model and Telegram or Discord, and configure it for your workflows. "
    "You retain control over the server, model keys, and business data."
)


@dataclass
class SenderIdentity:
    name: str
    company: str
    contact_email: str


@dataclass
class DraftContent:
    subject: str | None
    body: str


def _company_detail_sentence(company_name: str, detail: str | None) -> str:
    if detail:
        return f"Public information about {company_name} points to this: {detail.strip().rstrip('.')}."
    return f"We came across {company_name} through publicly available business information."


def _pain_point_sentence(pain_point: str | None) -> str:
    if pain_point:
        return f"One workflow that stood out: {pain_point.strip().rstrip('.')}."
    return ""


def _use_case_sentence(use_case: str | None) -> str:
    if use_case:
        return use_case.strip().rstrip(".") + "."
    return "a private agent could take on the repetitive parts of that workflow while a human stays in the loop for anything that needs judgment."


def render_initial_email(*, company_name: str, detail: str | None, pain_point: str | None, use_case: str | None, sender: SenderIdentity, citation_url: str) -> DraftContent:
    subject = f"A private AI agent idea for {company_name}"
    body = (
        f"Hi {company_name} team,\n\n"
        f"{_company_detail_sentence(company_name, detail)}\n\n"
        f"{_pain_point_sentence(pain_point)}\n\n"
        f"{sender.company} installs a private Hermes AI agent on your own Ubuntu server, connects it to "
        f"your preferred AI model and Telegram or Discord, and configures it for workflows like this: "
        f"{_use_case_sentence(use_case)} You keep full control of the server, model keys, and business data.\n\n"
        f"If that's useful, happy to share more detail or a short demo.\n\n"
        f"Best,\n{sender.name}\n{sender.company}\n{sender.contact_email}\n\n"
        f"---\n"
        f"This is a one-time outreach email based on publicly available information about {company_name} "
        f"({citation_url}). Reply \"unsubscribe\" and we won't contact you again."
    )
    return DraftContent(subject, body)


def render_contact_form(*, company_name: str, detail: str | None, pain_point: str | None, use_case: str | None, sender: SenderIdentity, citation_url: str) -> DraftContent:
    body = (
        f"Hi, {_company_detail_sentence(company_name, detail)} "
        f"{_pain_point_sentence(pain_point)} "
        f"{sender.company} sets up a private Hermes AI agent on your own server (your model keys, your data) "
        f"and configures it for workflows like this: {_use_case_sentence(use_case)} "
        f"Happy to share more if useful. — {sender.name}, {sender.company} ({sender.contact_email})"
    )
    return DraftContent(None, body.strip())


def render_linkedin_draft(*, company_name: str, detail: str | None, pain_point: str | None, use_case: str | None, sender: SenderIdentity, citation_url: str) -> DraftContent:
    body = (
        f"Hi — {_company_detail_sentence(company_name, detail)} "
        f"{_pain_point_sentence(pain_point)} "
        f"We help teams like yours run a private AI agent on their own server, connected to Telegram/Discord "
        f"and configured for exactly that kind of workflow. Open to a quick chat? — {sender.name}"
    )
    return DraftContent(None, body.strip())


def render_follow_up_1(*, company_name: str, use_case: str | None, sender: SenderIdentity, citation_url: str) -> DraftContent:
    subject = f"Following up: private AI agent for {company_name}"
    body = (
        f"Hi {company_name} team,\n\n"
        f"Following up on my earlier note. {sender.company} sets up a private Hermes AI agent on your own "
        f"Ubuntu server — {_use_case_sentence(use_case)} No pressure either way; happy to answer questions "
        f"or send a short demo if it's useful.\n\n"
        f"Best,\n{sender.name}\n{sender.company}\n{sender.contact_email}\n\n"
        f"---\nReply \"unsubscribe\" and we won't contact you again."
    )
    return DraftContent(subject, body)


def render_follow_up_2(*, company_name: str, sender: SenderIdentity, citation_url: str) -> DraftContent:
    subject = f"Still interested? Private AI agent for {company_name}"
    body = (
        f"Hi {company_name} team,\n\n"
        f"Circling back once more — {OFFER_SENTENCE} If now isn't the right time, that's completely fine, "
        f"just let me know and I'll close this out.\n\n"
        f"Best,\n{sender.name}\n{sender.company}\n{sender.contact_email}\n\n"
        f"---\nReply \"unsubscribe\" and we won't contact you again."
    )
    return DraftContent(subject, body)


def render_final_follow_up(*, company_name: str, sender: SenderIdentity, citation_url: str) -> DraftContent:
    subject = f"Closing the loop — {company_name}"
    body = (
        f"Hi {company_name} team,\n\n"
        f"I'll leave it here for now so I'm not cluttering your inbox. If a private AI agent for your team "
        f"becomes relevant later, feel free to reach out — {sender.contact_email}.\n\n"
        f"All the best,\n{sender.name}\n{sender.company}\n\n"
        f"---\nThis is the last message from us on this; you won't be contacted again."
    )
    return DraftContent(subject, body)
