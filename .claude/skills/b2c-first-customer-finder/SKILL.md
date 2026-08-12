---
name: b2c-first-customer-finder
description: Finds evidence-backed potential first customers for a B2C (consumer-facing) product or service from recent public signals — people who are actively complaining, asking for recommendations, or venting about the exact problem the business solves. Use when the user shares a business/product URL or description and asks to find early customers, beta users, first buyers, or launch leads for a consumer product (not a B2B/enterprise tool). Produces a scored, sourced shortlist plus a polished HTML report with suggested (public, consent-respecting) outreach openers.
---

# B2C First Customer Finder

Adapted for Claude Code from the open-source Codex skill `first-customer-finder` (Kappaemme, MIT).
This version is re-scoped for **B2C**: individual consumers, not companies or job titles. That
single change affects almost everything — where signals live, how "fit" is scored, and above all
how outreach is done, since DMing private strangers carries real ethical and legal weight that
B2B cold outreach doesn't. Read `references/outreach-ethics.md` before drafting any openers.

## When to use this skill

Trigger when the user gives a consumer product/service (URL, App Store listing, landing page, or
just a description) and asks something like: "find my first customers," "who should I launch to,"
"find beta testers," "who's complaining about [problem] online," or "find people who need this."

Do NOT use this for B2B/enterprise targets (company accounts, job titles, firmographics) — that's
a different motion (ICP → account list → decision-maker outreach). This skill is for individuals.

## Workflow

### Step 1 — Understand the business
Read whatever the user gave you (fetch the URL if provided). Extract in your own words:
- What the product/service actually does, in one sentence a non-technical person would understand
- The core problem it solves and for whom
- Price point / format (free, subscription, one-time purchase, local service, app, physical good)
- Any constraint that matters for targeting (geography for local services, platform for apps, age
  restrictions, etc.)

If the input is too thin to do this (e.g. just "find customers for my startup"), ask one
clarifying question rather than guessing — see `ask_user_input` guidance below.

### Step 2 — Build the Consumer ICP (Ideal Customer Profile)
Unlike B2B, a B2C ICP is built from **life situation and behavior**, not job title or company size.
Define, briefly:
- **Trigger moments**: what life event, purchase, or frustration puts someone in-market right now
  (moved house, new baby, injured a knee, got scammed by a competitor, New Year's resolution, etc.)
- **Where they'd vent or ask**: which subreddits, Facebook Groups, Nextdoor, local forums, App
  Store/Play Store reviews of competitors, Google/Yelp reviews, TikTok/Instagram comment sections,
  Reddit "recommend me a ___" threads
- **Language they'd use**: the actual phrases a frustrated consumer types, not marketing language
  (e.g. "does anyone actually work" not "seeking a reliable solution")

See `references/signal-sources.md` for a starting map of where B2C pain signals cluster by category
(local services, apps/SaaS-for-consumers, physical products, health/wellness, finance, etc.)

### Step 3 — Search for public pain/demand signals
Use web_search (and web_fetch on promising threads) to find **recent** (favor last 30–90 days
unless the user wants evergreen) public posts where someone:
- Explicitly asks for a recommendation matching this problem
- Complains about a competitor or the status quo way of solving it
- Describes the exact pain point unprompted (e.g. in a rant, a "PSA," a review)

Run multiple targeted queries — don't rely on one search. Vary:
- `site:reddit.com "[problem phrase]"` 
- `site:reddit.com "does anyone know" [category]`
- `"[competitor name]" review site:trustpilot.com OR site:reddit.com`
- Local variants with city/neighborhood names for local services
- App store review search for app-based competitors

For each promising thread, fetch it to confirm the person is real, the post is public, and the
context matches (not sarcasm, not already solved, not a bot/spam post).

### Step 4 — Qualify and score each prospect
For every candidate, capture:
- **Who**: username/handle only — never real name/PII unless they've publicly self-identified with it
- **Source**: direct URL to the post/comment/review (mandatory — no source, no entry)
- **Quote**: the exact line that shows the signal (short, verbatim, attributed)
- **Fit score (1–5)**: how closely their stated need matches the product
- **Timing score (1–5)**: how urgent/current the signal is (posted today vs. 8 months ago)
- **Reachability score (1–5)**: can they realistically be reached in a way that isn't creepy —
  public comment reply > public forum reply > platform DM to an open inbox. Score 1 if the only
  path is scraping contact info or DMing someone who has DMs closed/hasn't consented to contact.

Drop anything with a Reachability score of 1 from the outreach list — you can still log it as a
demand-signal data point, just don't draft outreach for it.

### Step 5 — Draft outreach openers (public-first, consent-respecting)
For each prospect with Reachability ≥ 2, draft ONE short, human, non-salesy opener that:
- References their specific public post (proves you read it, not spray-and-pray)
- Is honest about who you are and why you're reaching out (you're building the thing, not a bot)
- Offers something free/low-friction first (early access, a real answer to their question, not a pitch)
- Defaults to a **public reply** on the same thread over a DM wherever the platform allows it —
  public replies also help the next person who finds that thread
- Is short enough to read in one glance (2–4 sentences)

Never draft anything that: pretends to be a fellow customer/plant, buys engagement, mass-DMs a
list, or scrapes an email/phone number the person didn't post publicly for that purpose.

### Step 6 — Build the report
Use `assets/report_template.html` as the base. Populate:
- Business summary (from Step 1)
- Consumer ICP (from Step 2)
- Ranked shortlist table: name/handle, source link, quote, fit/timing/reachability scores, opener
- A short "demand signal" summary even for the dropped (unreachable) entries — useful market
  validation even if you can't outreach them directly

Save as an artifact (`.html`) so the user can open and share it. Use the `docx` skill instead if
the user explicitly wants a Word doc.

## Guardrails (read this before Step 5)
This skill searches and cites **public** posts only. It never:
- Scrapes personal contact details, private profiles, or anything behind a login
- Recommends cold-emailing/cold-calling a private individual using data they didn't post publicly
- Treats a public post as consent to unlimited or automated outreach — one thoughtful reply, not a drip sequence
- Fabricates a prospect, quote, or source link — if you can't find a real one, say so and report the gap honestly

Full detail in `references/outreach-ethics.md` — treat it as non-negotiable, not optional reading.
