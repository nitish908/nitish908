# b2c-first-customer-finder (Claude Code skill)

A Claude Code / Cowork skill that finds evidence-backed potential **first customers** for a
consumer (B2C) product from recent public signals — reworked from the open-source Codex skill
`first-customer-finder` by Kappaemme (MIT). Re-scoped for individuals instead of companies, with
stricter outreach guardrails since you're talking to private people, not job titles.

## What it does
1. Reads your product/business (URL or description) and summarizes it
2. Builds a consumer ICP — trigger moments, where they'd vent online, the language they'd use
3. Searches public forums/reviews/social for people showing that exact pain or asking for a fix
4. Scores each one on fit / timing / reachability, with a source link and verbatim quote for every entry
5. Drafts one honest, non-salesy public-reply opener per reachable prospect
6. Outputs a polished HTML report — plus an honest log of real signals that aren't safe to outreach

## Install

**Project-level** (this repo only):
```bash
mkdir -p .claude/skills
cp -R b2c-first-customer-finder .claude/skills/b2c-first-customer-finder
```

**Personal / all projects**:
```bash
mkdir -p ~/.claude/skills
cp -R b2c-first-customer-finder ~/.claude/skills/b2c-first-customer-finder
```

Claude Code auto-discovers skills from `.claude/skills/` — no restart required, just start a new
task and mention what you want.

## Usage
Just describe the ask naturally — no slash command needed:

> "Find my first customers for [product URL]. It's a B2C app for X."

> "Who's out there complaining about [problem] that my product solves? Build me a report."

## Files
- `SKILL.md` — the skill definition Claude reads
- `references/signal-sources.md` — where B2C pain signals live, by category
- `references/outreach-ethics.md` — hard rules for consumer outreach (read before sending anything)
- `assets/report_template.html` — the output report template

## License
MIT, same as the original. Credit: concept adapted from Kappaemme-git/codex-first-customer-finder-skill.
