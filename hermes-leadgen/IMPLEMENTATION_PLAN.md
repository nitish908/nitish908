# Hermes Lead-Generation Platform — Implementation Plan

## 0. Repository context (Phase 1 findings)

This repository (`nitish908/nitish908`) currently hosts an unrelated open-source
project: the **Universal LLM Context Schema (ULCS)** — a TypeScript pnpm
monorepo (`packages/`, `specification/`, `schemas/`, `website/`, `benchmark/`).
There is no existing backend, frontend, database, or CRM code to reuse for a
lead-generation platform.

Per explicit user direction, the new platform is built as a self-contained
subtree at `hermes-leadgen/` in this same repository, without touching any
ULCS files. Nothing under the repo root outside `hermes-leadgen/` is modified.

## 1. Scope decisions for the MVP

This is a large spec (CRM, scoring engine, research pipeline, outreach
generation, approval queue, dashboards, scheduled jobs, compliance docs,
security docs, tests). Building it incrementally, phase by phase, with a
commit after each phase. Simplifications made and documented as assumptions:

- **Live sending stays disabled by default everywhere.** Email/CRM "send"
  actions only produce drafts + CSV export in the MVP; provider interfaces
  (SMTP/SendGrid-shaped) exist but are feature-flagged off
  (`OUTREACH_LIVE_SEND_ENABLED=false`).
- **Lead sources implemented for MVP:** CSV upload, manual entry, and public
  website research (fetch + parse permitted pages). Google Places / Product
  Hunt / GitHub org connectors are built as a provider interface with one
  working reference connector (GitHub public org API, since it needs no paid
  key) and clearly marked "not configured" stubs for Google Places / Product
  Hunt, matching the "clearly mark unconfigured optional providers" rule.
- **AI analysis provider:** OpenAI-compatible client (works with Ollama or
  hosted OpenAI-compatible endpoints) via `OPENAI_BASE_URL` / `OPENAI_API_KEY`
  env vars. If unset, scoring/research/outreach fall back to deterministic
  rule-based logic (no LLM required to run the MVP end-to-end).
- **Auth:** single-tenant, username/password + JWT session cookie, one
  built-in "owner" role plus "viewer" role (RBAC skeleton, not a full
  multi-org system).
- **Scheduling:** Celery beat drives the daily workflow; a manual "Run now"
  API/button exists for demoing without waiting on a cron.

## 2. Architecture

```
hermes-leadgen/
  backend/            FastAPI + SQLAlchemy + Alembic + Celery
  frontend/            Next.js (App Router) + TS + Tailwind + shadcn/ui
  docs/                 architecture, API, security, compliance, deployment, backup, roadmap
  sample_data/          demo CSV
  docker-compose.yml
  .env.example
```

Backend modules: `core` (config/db/security/ssrf-guard), `models`, `schemas`,
`api` (routers), `services` (scoring, research, outreach, dedup, suppression,
csv import, connectors/), `workers` (Celery tasks + beat schedule), `alembic`.

## 3. Phases (each ends with a commit + push + status update)

1. **Phase 1 (this doc):** inspect repo, plan, scaffold directories. ✅
2. **Phase 2:** DB models + Alembic migrations, auth, CRM core (leads,
   stages, notes, activity log, tasks, suppression list, audit log), CSV
   import + dedup, scoring engine + config API.
3. **Phase 3:** website research pipeline with SSRF guard, robots.txt check,
   content sanitization / prompt-injection isolation, evidence storage.
4. **Phase 4:** outreach draft generation + human approval queue, CSV export,
   disabled-by-default send providers.
5. **Phase 5:** Next.js dashboard pages, Celery beat daily workflow, reports,
   frontend/backend tests, full documentation set.
6. **Phase 6:** run migrations, run backend + frontend tests/lint, fix
   issues, execute the CSV → approved-draft demo workflow end to end.

## 4. Non-negotiables carried through every phase

- No credentials in source; `.env.example` only.
- SSRF guard blocks localhost/private/link-local/cloud-metadata ranges for
  every outbound fetch (research pipeline, webhook-style calls).
- Fetched website content is always treated as inert data appended to a
  prompt, never as instructions; the LLM call for research uses a system
  prompt that explicitly rejects instructions found in page content, and the
  app never executes actions suggested by page content.
- Nothing is sent to a lead without an explicit human approval record
  (recipient + channel + content hash + scheduled time all match what was
  approved).
- Every collected field carries `source_name` + `source_url` attribution.
- No email address is ever synthesized — only captured if displayed on a
  page the user is shown a citation for.
