# Demo Workflow: CSV → Approved Draft

A step-by-step walkthrough of the golden path, using
`sample_data/leads_sample.csv` (five fictional companies matching the
target customer profiles: an AI automation agency, a content-creation
agency, a consulting practice, a small software company, and an
e-commerce marketplace).

Prerequisites: the stack is running (`docker compose up --build` from
`hermes-leadgen/`, or the equivalent local dev setup) and you're logged in
at `http://localhost:3000`.

## 1. Import leads

Go to **Lead discovery** → **CSV upload** → choose
`sample_data/leads_sample.csv`. You should see:

> Imported 5 leads (0 duplicates, 0 suppressed skipped).

Go to **Leads** — all five now appear with `stage = discovered`, no score
yet.

## 2. Research a lead

Click into **Pixel & Pine Automation Agency** (the strongest-fit lead in
the sample data — it mentions Slack, Telegram, and automation directly).
Click **Research website**. Within a few seconds you'll see:

- **Research findings**: a summary, and (if an AI provider is configured
  via `OPENAI_BASE_URL`) a pain point / use case / suggested package —
  each marked `(verified)` or `(assumption)`, with a citation link back to
  the exact page used
- **Pages fetched**: the specific URLs the research pipeline visited,
  and whether `robots.txt` allowed each one

Without an AI provider configured, you'll still get a rule-based summary
and (if the page text matches known patterns) a pain point/use case — the
MVP works end-to-end without any AI provider.

## 3. Score the lead

Click **Re-score**. The score jumps (this lead should land in the 70s–90s
range, "hot") and **Score evidence** lists exactly which of the 8 rules
fired, with the specific text that matched and (where applicable) which
page it came from. Every point on the score is explained — nothing is a
black box.

## 4. Generate an outreach draft

Still on the lead page, under **Generate outreach draft**, click
**initial email**. You'll see:

> Draft created and added to the approval queue.

## 5. Review and approve

Go to **Approval queue**. Your draft is there with `status: pending`,
showing:
- The full subject + body, editable inline
- The **cited company detail** the draft's opening line is built from —
  cross-check it against what you saw in Research findings

Edit the body if you want (click **Save edit**), then click **Approve**.

## 6. Confirm nothing gets sent automatically

Click **Send now** on the now-approved draft. You'll get:

> Live sending is disabled in this deployment (OUTREACH_LIVE_SEND_ENABLED=false).
> Use the CSV export in the approval queue to send manually.

This is the expected, intentional behavior for the MVP — see
`docs/COMPLIANCE_CHECKLIST.md`. Click **Export CSV** to get the approved
message ready to paste into your own email client, or configure SMTP and
`OUTREACH_LIVE_SEND_ENABLED=true` once you've reviewed the compliance
checklist for your market.

## 7. Run the full daily workflow at once

Instead of steps 2–4 one lead at a time, you can run the whole pipeline
(research → score → draft hot/warm leads → surface follow-ups) in one
shot: **Settings** page confirms your role is `owner`, then:

```bash
curl -X POST http://localhost:8000/api/workflow/run-now \
  -b cookies.txt -H "X-CSRF-Token: <token>"
```

(Or trigger it from the API docs at `/docs` while logged in via the
browser — cookies carry over.) The response is the same JSON shape shown
on **Overview**/**Reports**, plus this run's counts and any errors:

```json
{
  "new_leads": 5, "hot_leads": 1, "warm_leads": 1,
  "drafts_awaiting_approval": 1,
  "leads_researched_this_run": 5, "leads_scored_this_run": 5,
  "drafts_created_this_run": 1, "follow_ups_due_count": 0, "errors": []
}
```

## 8. Check the CRM board and reports

- **Campaigns** shows the kanban board — your researched/scored/drafted
  leads have moved from `discovered` through `researching` →
  `qualified`/`draft_ready`.
- **Reports** shows the funnel metrics and breakdowns by industry/source/
  score tier, all computed live from the leads you just imported.
- **Compliance** shows the suppression list (empty for now) and audit log
  (every action you just took, including who and when).

That's the full golden path from a CSV file to a human-approved,
export-ready outreach draft — with every fact traceable to a source, every
score explained, and nothing sent without your explicit approval.
