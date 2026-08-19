# Architecture

## Overview

```
                     ┌──────────────────────┐
                     │   Next.js frontend    │  cookie session + CSRF token
                     │  (App Router, client   │──────────────┐
                     │   components + fetch)  │              │
                     └──────────────────────┘              │
                                                              ▼
┌──────────────┐        ┌───────────────────────────────────────────┐
│  PostgreSQL   │◄──────►│              FastAPI backend                │
│  (SQLAlchemy  │        │  api/routers -> services -> models (ORM)    │
│   + Alembic)  │        │  auth (JWT cookie) · CSRF · RBAC · audit log │
└──────────────┘        └───────────────────────────────────────────┘
       ▲                                │        ▲
       │                                │        │ enqueue / poll
       │                        ┌───────▼───┐  ┌──▼──────┐
       │                        │  Celery    │  │ Celery   │
       └────────────────────────│  worker    │  │ beat     │
                                 │ (daily     │  │ (07:00   │
                                 │  workflow) │  │  UTC)    │
                                 └───────────┘  └──────────┘
                                        │
                                        ▼
                              ┌──────────────────┐
                              │ Redis (broker +   │
                              │ result backend)    │
                              └──────────────────┘

Outbound to the public internet only from: the research fetcher (SSRF-guarded,
robots.txt-checked, rate-limited), lead-source connectors (GitHub API, etc.),
and (if configured) the AI provider / SMTP.
```

## Backend layout (`backend/app/`)

- `core/` — cross-cutting concerns: `config.py` (env-var settings),
  `db.py` (SQLAlchemy engine/session), `security.py` (password hashing,
  JWT, provider-credential encryption), `csrf.py` (double-submit CSRF),
  `ssrf_guard.py` (outbound-URL safety), `audit.py` (audit log writer).
- `models/` — SQLAlchemy ORM models, one file per concern (`lead.py`,
  `scoring.py`, `research.py`, `outreach.py`, `crm.py`, `source.py`,
  `user.py`). `enums.py` holds every fixed vocabulary (stages, tiers,
  message types, statuses) used across models, schemas, and services.
- `schemas/` — Pydantic request/response models for the handful of routes
  that use `response_model` (most routes return hand-built dicts, which
  keeps the JSON shape close to the SQL query rather than round-tripping
  through an ORM object).
- `api/routers/` — one FastAPI router per resource area (`auth`, `leads`,
  `scoring`, `sources`, `research`, `outreach`, `crm`, `reports`,
  `settings`, `workflow`). Routers stay thin: request parsing, permission
  checks, calling a service function, shaping the response.
- `services/` — the actual business logic, framework-agnostic so it's
  reusable from both API routers and the Celery task:
  - `dedup.py`, `csv_import.py`, `suppression.py` — lead intake
  - `scoring_engine.py` — the configurable 100-point scoring engine
  - `connectors/` — the lead-source provider architecture (see below)
  - `research/` — `fetcher.py` (SSRF+robots-safe HTTP), `sanitizer.py`
    (HTML→text, strips scripts/hidden content), `analyzer.py`
    (prompt-injection-resistant LLM analysis + rule-based fallback),
    `orchestrator.py` (ties them together, persists findings/citations)
  - `outreach/` — `templates.py` (the six message templates),
    `generator.py` (fills a template from verified lead/research fields),
    `queue.py` (generate + create the pending `ApprovalRecord`),
    `email_provider.py` (SMTP interface, never called unless explicitly
    enabled and approved)
  - `reports.py` — the metric queries backing the dashboard and the daily
    summary (shared so the API and the Celery task can't disagree)
  - `llm_client.py` — minimal OpenAI-compatible chat client (works with
    Ollama); every caller has a deterministic non-AI fallback
- `workers/` — `celery_app.py` (Celery + beat schedule), `tasks.py` (the
  daily workflow)
- `alembic/` — migrations, one linear history starting from `initial schema`

## Frontend layout (`frontend/`)

Next.js App Router, plain client components (`"use client"`) that call the
backend directly via `lib/api.ts` (adds the CSRF header, `credentials:
"include"` for the cookie session). No server-side data fetching or
Server Actions are used, which keeps the auth model simple (one httpOnly
session cookie + one readable CSRF cookie) and avoids a whole class of
Next.js Server Component/Action CVEs (see
[SECURITY_THREAT_MODEL.md](./SECURITY_THREAT_MODEL.md)).

- `app/<page>/page.tsx` — one route per dashboard section from the spec
- `components/ui/` — a small shadcn-style primitive set (Button, Card,
  Badge, Input/Textarea) built on `class-variance-authority` +
  `tailwind-merge`, not the full shadcn CLI-generated library
- `lib/api.ts` — fetch wrapper (CSRF header, error shaping, CSV blob
  handling); `lib/auth.ts` — `useRequireAuth()` hook that redirects to
  `/login` on a 401

## The lead-source connector architecture

`services/connectors/base.py` defines a `Connector` ABC with
`is_configured` and `discover(limit)`. Adding a new source means writing
one class and registering it — the CSV import, manual entry, and website
research paths don't go through this interface (they're their own
services), but any *automated* discovery source does:

- `github_org.py` — real, working connector using GitHub's official REST
  API (works unauthenticated at a low rate limit, or with `GITHUB_TOKEN`)
- `unconfigured_stubs.py` — Google Places and Product Hunt connectors that
  report `is_configured = False` until their API keys are set, so the UI
  can clearly mark them unavailable instead of silently doing nothing

## Data flow: CSV → approved draft

1. `services/csv_import.py` parses the CSV, checks each row against
   `SuppressionEntry` and existing leads (`dedup.py`), creates a `Lead` +
   `LeadFieldAttribution` rows for every populated field.
2. `services/research/orchestrator.py` fetches permitted pages
   (SSRF-guarded, robots.txt-checked), sanitizes them, and asks the
   analyzer for a summary/pain-point/use-case/package — stored as
   `ResearchFinding` rows with a citation URL and verified/assumption
   confidence.
3. `services/scoring_engine.py` evaluates the configurable rules against
   the lead's fields + research findings, storing `ScoreEvidence` per rule
   and setting `Lead.score` / `Lead.tier`.
4. `services/outreach/queue.py` generates a draft (`OutreachMessage`) from
   verified fields only and creates a `pending` `ApprovalRecord`.
5. A human reviews/edits/approves in the approval queue. Sending is gated
   by `OUTREACH_LIVE_SEND_ENABLED` **and** an exact content-hash match
   between the approved and current message content **and** the lead not
   being suppressed — see `api/routers/outreach.py::send_now`.

## Why some things are simpler than the full spec

See `IMPLEMENTATION_PLAN.md` §1 for the full list of MVP scope decisions
(rule-based-only outreach copy, single-tenant RBAC, in-process rate
limiting) and `docs/ROADMAP.md` for what graduates them beyond the MVP.
