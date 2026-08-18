# Compliance Checklist

**This software does not guarantee legal compliance with any anti-spam or
privacy law.** Anti-spam, marketing, and data-protection requirements
(CAN-SPAM, GDPR, PECR, India's Digital Personal Data Protection Act, and
others) vary by where your business operates, where your recipients are
located, and how you use this tool. **Get advice from a qualified lawyer
for your target market before sending outreach at any meaningful scale.**
This checklist is an operator aid, not legal advice, and is almost
certainly incomplete for your specific situation.

## What the platform does for you

- [x] Never sends a message without explicit human approval of the exact
      recipient, channel, content, and send time (`ApprovalRecord` content
      hash match, see `docs/SECURITY_THREAT_MODEL.md` §3)
- [x] Never fabricates or guesses an email address — only stores one found
      explicitly published on a page it can cite
- [x] Every collected field carries source attribution
      (`LeadFieldAttribution`: source name, URL, timestamp)
- [x] Maintains a suppression list checked before every discovery, draft,
      and send step (`SuppressionEntry`, `services/suppression.py`)
- [x] Provides an opt-out / unsubscribe line on every email-channel
      template (`services/outreach/templates.py`)
- [x] Rejecting a draft can simultaneously mark the lead do-not-contact
      (approval-queue "Reject & do not contact")
- [x] Records every security- and compliance-relevant action to an
      immutable audit log (`AuditLogEntry`)
- [x] Configurable data-retention period (`LEAD_DATA_RETENTION_DAYS`) —
      see below for what "configurable" means today
- [x] Respects `robots.txt` and rate-limits the research pipeline
      per-domain
- [x] Only collects publicly available business information; no
      sensitive personal data fields exist in the data model
- [x] Live outreach sending stays disabled (`OUTREACH_LIVE_SEND_ENABLED=false`)
      until an operator explicitly turns it on

## What the operator must still do

- [ ] **Get jurisdiction-specific legal advice** before sending outreach
      to any region (this cannot be a checkbox this software satisfies
      for you)
- [ ] Decide your lawful basis for contacting each recipient (e.g.
      legitimate interest under GDPR, or an equivalent basis under your
      applicable law) — this platform does not make that determination
- [ ] Configure `SENDER_NAME`, `SENDER_COMPANY`, `SENDER_CONTACT_EMAIL` to
      real, monitored values before enabling live sending — every
      generated message identifies the sender using these
- [ ] Actually process unsubscribe replies: this platform's draft
      templates ask a recipient to reply "unsubscribe", but **nothing
      currently parses inbound email replies automatically** — an
      operator must manually check the inbox tied to
      `SENDER_CONTACT_EMAIL` and add unsubscribes to the suppression list
      via the Compliance page (or `POST /api/crm/suppression-list`).
      Automating this is on `docs/ROADMAP.md`.
- [ ] Honor data-subject access/deletion requests within your
      jurisdiction's required timeframe — see "Data deletion" below
- [ ] Set `LEAD_DATA_RETENTION_DAYS` to a value your legal counsel signs
      off on, and actually run a retention job (see below — this is not
      yet automated)
- [ ] Review the six outreach templates yourself for tone/claims before
      relying on them at scale — automated generation reduces but does
      not eliminate the need for human review of message content
- [ ] Decide whether GitHub org data (public repos/profile info) is an
      acceptable lead source for your jurisdiction — it's public data, but
      "public" and "lawful to use for marketing" are not the same test
      everywhere

## Data deletion

There is no automated retention-enforcement job in the MVP —
`LEAD_DATA_RETENTION_DAYS` is stored and surfaced in Settings, but nothing
currently deletes aged-out records automatically (tracked in
`docs/ROADMAP.md`). To delete a lead and its related data manually today:

```sql
-- Run against the Postgres database. Replace the UUID.
DELETE FROM score_evidence WHERE lead_id = '...';
DELETE FROM research_findings WHERE lead_id = '...';
DELETE FROM research_page_fetches WHERE lead_id = '...';
DELETE FROM lead_field_attributions WHERE lead_id = '...';
DELETE FROM lead_notes WHERE lead_id = '...';
DELETE FROM lead_activities WHERE lead_id = '...';
DELETE FROM lead_tasks WHERE lead_id = '...';
DELETE FROM outreach_messages WHERE lead_id = '...';
DELETE FROM approval_records WHERE lead_id = '...';
DELETE FROM leads WHERE id = '...';
```

For a full account/business deletion request, also remove any matching
`suppression_entries` only if the requester explicitly asks to be
re-contactable in future (normally you'd *keep* their suppression entry
so you don't accidentally re-add them).

## CAN-SPAM specifics (US recipients)

If any of your outreach targets US-based recipients, the CAN-SPAM Act
requires (non-exhaustive): accurate header/sender information (satisfied
if `SENDER_*` env vars are accurate), a clear and conspicuous opt-out
mechanism (the templates include one; you must honor it within 10
business days), a valid physical postal address in the message (**not
currently included in the templates — add one before sending to US
recipients**), and no deceptive subject lines.

## GDPR / PECR specifics (UK/EU recipients)

B2B marketing email to a named individual generally still requires a
lawful basis and, under PECR, specific rules for unsolicited electronic
marketing depending on recipient type (sole trader/partnership vs.
limited company) and prior relationship. This platform does not implement
consent tracking beyond the suppression list — treat `consent_status` on
the `Lead` model as a placeholder field to extend, not a compliance
feature on its own.

## India (DPDP Act) specifics

If processing personal data of individuals in India, review the Digital
Personal Data Protection Act's notice-and-consent requirements. Business
contact information for a company (not an individual) is generally
outside DPDP's scope, but a named individual's business email may not be.
