# API Reference

Interactive docs (Swagger UI) are available at `/docs` on a running
backend, and the raw OpenAPI schema at `/openapi.json`. This page is a
narrative map of the endpoints — see `/docs` for exact request/response
schemas.

**Auth:** every endpoint except `/api/auth/login` and `/api/health`
requires the `hermes_session` httpOnly cookie (set by login). Every
state-changing request (`POST`/`PATCH`/`DELETE`) additionally requires an
`X-CSRF-Token` header matching the `csrf_token` cookie value.

## Auth — `/api/auth`

| Method & path | Description |
|---|---|
| `POST /login` | `{email, password}` → sets session + CSRF cookies |
| `POST /logout` | clears cookies |
| `GET /me` | current user |

## Leads — `/api/leads`

| Method & path | Description |
|---|---|
| `GET /` | list, filterable by `stage`, `tier`, `industry`, `q` |
| `GET /{id}` | lead detail |
| `POST /` | manual lead entry (rejects duplicates/suppressed) |
| `PATCH /{id}` | update stage/owner/follow-up/etc.; logs stage changes to activity |
| `POST /{id}/score` | re-run the scoring engine for this lead |
| `POST /import-csv` | multipart CSV upload → dedup + suppression-filtered import |
| `GET /export/csv` | export all leads as CSV |
| `POST /{id}/notes`, `GET /{id}/notes` | lead notes |
| `GET /{id}/activity` | stage-change / note / send history |
| `POST /{id}/tasks` | add a follow-up task |
| `POST /{id}/research`, `GET /{id}/research` | run/read the website research pipeline |

## Scoring — `/api/scoring`

| Method & path | Description |
|---|---|
| `GET /rules` | the 8 configurable scoring rules (seeds defaults on first call) |
| `PATCH /rules/{id}` | edit a rule's weight/enabled/thresholds (**owner only**) |
| `GET /leads/{id}/evidence` | per-rule evidence for a lead's score |

## Lead sources — `/api/sources`

| Method & path | Description |
|---|---|
| `GET /providers` | status of every connector (configured vs. not) |
| `GET /`, `POST /` | list/create configured source instances |
| `POST /{id}/run` | run a connector's `discover()` once, dedup+suppress, create leads |

## Outreach & approval queue — `/api/outreach`

| Method & path | Description |
|---|---|
| `POST /leads/{id}/drafts` | generate a draft (`{message_type}`) and queue it for approval |
| `GET /leads/{id}/drafts` | list drafts for a lead |
| `PATCH /messages/{id}` | edit a draft's subject/body before approval |
| `GET /approval-queue` | list by `status_filter` (`pending` default) |
| `POST /approvals/{id}/approve` | `{channel?, scheduled_send_at?}` |
| `POST /approvals/{id}/reject` | `{reason?, prevent_future_contact?}` |
| `POST /approvals/{id}/send` | send now — **refuses unless** `OUTREACH_LIVE_SEND_ENABLED=true`, the approval is `approved`/`scheduled`, the content hash still matches, and the lead isn't suppressed |
| `GET /export/csv` | export the approval queue as CSV (for manual sending) |

## CRM — `/api/crm`

| Method & path | Description |
|---|---|
| `GET /kanban` | leads grouped by stage |
| `GET /follow-ups-due` | leads whose `next_follow_up_at` has passed |
| `GET /tasks` | open tasks across all leads |
| `GET /suppression-list`, `POST /suppression-list` | view/add suppressed emails or domains |
| `GET /audit-log` | security-relevant action log (**owner only**) |

## Reports — `/api/reports`

| Method & path | Description |
|---|---|
| `GET /overview` | dashboard metrics (funnel counts, breakdowns by industry/source/tier) |
| `GET /daily-summary` | last-24h counts for the daily-workflow summary view |

## Workflow — `/api/workflow`

| Method & path | Description |
|---|---|
| `POST /run-now` | runs the daily workflow synchronously (**owner only**) — same logic as the Celery beat schedule, for demos |

## Settings — `/api/settings`

| Method & path | Description |
|---|---|
| `GET /` | non-secret operational flags (never returns credentials) |

## Error format

Errors are `{"detail": "human-readable message"}` with an appropriate HTTP
status (400/401/403/404/409/502). `422` is FastAPI's own validation-error
shape for malformed request bodies.
