# Roadmap

Ordered roughly by what unblocks the most value next, not by difficulty.

## Near-term (unblocks real usage)

- **Live sending, done carefully.** The SMTP provider interface already
  exists (`services/outreach/email_provider.py`); turning
  `OUTREACH_LIVE_SEND_ENABLED=true` on wires it up. Before recommending
  this to a real operator: add bounce/complaint handling, a real physical
  mailing address in the email templates (CAN-SPAM requirement), and rate
  limiting on sends per domain/day.
- **Inbound reply handling.** Nothing currently parses inbound email
  replies (for "unsubscribe" detection or marking a lead `replied`). An
  IMAP poller or a provider webhook (SendGrid inbound parse, etc.) that
  creates a `LeadActivity` and optionally auto-suppresses on "unsubscribe"
  language would close a real gap flagged in
  `docs/COMPLIANCE_CHECKLIST.md`.
- **Automated data-retention enforcement.** `LEAD_DATA_RETENTION_DAYS` is
  stored and shown in Settings but nothing deletes aged-out records yet.
  A scheduled Celery task mirroring the manual SQL in
  `docs/COMPLIANCE_CHECKLIST.md` would close this.
- **Dashboard-editable outreach templates.** Templates are currently
  Python code (`services/outreach/templates.py`) for safety/predictability
  in the MVP. A template-editor UI backed by a `MessageTemplate` DB model
  (with the same "cited detail + one problem + one use case + opt-out"
  structural guarantees enforced at generation time, not left to the
  editor) is the natural next step.

## Lead sources

- **Google Places connector**, once a real API key + search-query
  strategy (location + business type, configurable per user) is decided.
  The connector class already exists
  (`services/connectors/unconfigured_stubs.py`) and just needs
  `discover()` implemented.
- **Product Hunt connector**, same shape.
- **Business directories that explicitly permit API access** — add as new
  `Connector` subclasses per the pattern in
  `services/connectors/base.py`; nothing in the rest of the app needs to
  change.
- **Distributed rate limiting for the research pipeline.** The current
  per-domain limiter is in-process (`services/research/fetcher.py`); move
  to Redis-backed counters before running multiple Celery workers
  concurrently against the research queue.

## Scoring & research

- **LLM-assisted scoring signal extraction** (currently keyword/substring
  matching). Would need the same prompt-injection discipline as the
  research analyzer, and should stay evidence-backed and explainable —
  don't trade away "explain exactly why the score was assigned" for a
  black-box classifier.
- **Multi-page-aware pain-point synthesis** — right now the analyzer looks
  at the pages fetched in one research run; a version that synthesizes
  across previously fetched pages (without re-fetching) could produce
  richer findings.

## CRM

- **Full RBAC** beyond owner/viewer — per-resource permissions, multiple
  owners with different lead pools, etc.
- **Duplicate detection beyond exact domain/name match** — fuzzy matching
  for near-duplicate company names, configurable similarity threshold.
- **Reply sentiment classification** to populate `positive_replies` in the
  reports (currently always `null` — deliberately not fabricated).

## Reporting

- **Estimated acquisition cost.** Currently always `null` in
  `/api/reports/overview` — computing it needs operator-provided cost
  inputs (ad spend, tool costs, time cost) this platform doesn't collect
  yet. Add a Settings field for monthly cost inputs and compute
  cost / won-deals.
- **Historical trend charts**, not just current-state counts.

## Infrastructure

- **CI pipeline** running `pytest` + `npm run typecheck && eslint && vitest`
  on every push (the repo's existing top-level CI is for the unrelated
  ULCS project this subtree lives alongside — a scoped workflow for
  `hermes-leadgen/` would need its own path filters).
- **Structured logging + error tracking** (Sentry or similar) beyond
  stdout logs and the audit-log table.
- **Managed-hosting mode**: since "fully managed Hermes hosting" is a
  planned future service per the business description, the natural
  extension is turning this same platform into the ops console for it —
  tracking which customers' Hermes Agent instances need updates, backups,
  monitoring alerts, etc. Out of scope for lead-gen but worth noting as
  the next product surface this codebase is positioned to grow into.
