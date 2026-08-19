# Hermes Lead-Generation Platform

Lead-generation and sales-assistance platform for a Hermes Agent
installation / managed-hosting business. Automates lead discovery,
qualification, research, personalization, CRM tracking, and follow-up
preparation — **it never sends a message without explicit human approval.**

> This subtree lives inside `nitish908/nitish908`, a repository that
> otherwise hosts an unrelated project (the Universal LLM Context Schema).
> Nothing outside `hermes-leadgen/` is touched by this platform. See
> [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) for how this came to
> be and the MVP scope decisions.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Celery + Redis, PostgreSQL
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, a small
  shadcn-style component set
- **Deployment:** Docker Compose (Postgres, Redis, backend, worker, beat,
  frontend)

## Quick start (local development)

```bash
cd hermes-leadgen
cp .env.example .env
# Fill in SECRET_KEY, CREDENTIALS_ENCRYPTION_KEY, and SEED_OWNER_* at minimum:
python3 -c "import secrets; print(secrets.token_urlsafe(48))"                                  # -> SECRET_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"     # -> CREDENTIALS_ENCRYPTION_KEY

docker compose up --build
```

This starts Postgres, Redis, the FastAPI backend (runs migrations + seeds
the scoring rules and your owner account on boot), a Celery worker, Celery
beat (the daily workflow, 07:00 UTC by default), and the Next.js frontend.

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs at `/docs`)

Sign in with `SEED_OWNER_EMAIL` / `SEED_OWNER_PASSWORD` from your `.env`.
To add more users later: `docker compose exec backend python scripts/create_user.py you@example.com 'a-strong-password' owner`.

## Demo workflow (CSV → approved draft)

See [`docs/DEMO_WORKFLOW.md`](./docs/DEMO_WORKFLOW.md) for a step-by-step
walkthrough using `sample_data/leads_sample.csv`.

## Running tests

```bash
# Backend (pytest, runs against an in-memory SQLite DB — no services needed)
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python -m pytest

# Frontend (vitest + typecheck + lint)
cd frontend && npm install
npm run typecheck && npx eslint . && npm test
```

## Documentation

- [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) — phased build plan and MVP scope decisions
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — system architecture
- [`docs/API.md`](./docs/API.md) — API reference
- [`docs/SECURITY_THREAT_MODEL.md`](./docs/SECURITY_THREAT_MODEL.md) — threats and mitigations
- [`docs/COMPLIANCE_CHECKLIST.md`](./docs/COMPLIANCE_CHECKLIST.md) — operator checklist (not legal advice)
- [`docs/DEPLOYMENT_UBUNTU.md`](./docs/DEPLOYMENT_UBUNTU.md) — production deployment on an Ubuntu VPS
- [`docs/BACKUP_RESTORE.md`](./docs/BACKUP_RESTORE.md) — backup and restore procedures
- [`docs/DEMO_WORKFLOW.md`](./docs/DEMO_WORKFLOW.md) — CSV-to-approved-draft walkthrough
- [`docs/ROADMAP.md`](./docs/ROADMAP.md) — what's next

## Core safety properties

- **Nothing is ever sent without human approval.** Every outbound message
  requires an `ApprovalRecord` whose recipient, channel, content hash, and
  scheduled time exactly match what's about to be sent; live sending is
  additionally gated behind `OUTREACH_LIVE_SEND_ENABLED=false` by default.
- **No fabricated facts.** Company data is only ever taken from a page the
  operator can see cited; nothing is guessed, including email addresses.
- **SSRF-safe research.** Every fetch validates the URL and every resolved
  DNS address against private/loopback/link-local/cloud-metadata ranges.
- **Prompt-injection resistant.** Fetched web content is always inert data
  in the LLM prompt, wrapped in explicit delimiters, never able to trigger
  tool calls or override instructions.
