# Vialactée — Review System

This directory contains all periodic project reviews. Reviews are the primary tool for tracking technical health, documentation accuracy, and agent effectiveness over time.

---

## Directory Structure

```
.agents/reviews/
├── README.md                        ← this file
├── CHANGELOG.md                     ← inter-review progress log (update as you work)
├── template_code_review.md          ← template for code/architecture audits
├── template_docs_review.md          ← template for documentation audits
├── template_webapp_review.md        ← template for web app / UI audits
├── wapp_screenshots/                ← folder for UI review screenshots
└── YYYY-MM-DD_[type]_review.md      ← dated review files
```

**Naming convention:** `YYYY-MM-DD_code_review.md`, `YYYY-MM-DD_docs_review.md`, or `YYYY-MM-DD_webapp_review.md`

---

## Review Types

| Type | Template | Scope | When to run |
|---|---|---|---|
| **Code Review** | `template_code_review.md` | Python core, hardware, web interface, playground | After a major feature ships or significant refactor |
| **Docs Review** | `template_docs_review.md` | All `.md` files, inline comments, agent-facing docs | After a code review surfaces stale docs, or every 2–3 code reviews |
| **Web App Review** | `template_webapp_review.md` | `wabb-interface/` — tabs, components, WebSocket, CSS | After any significant UI feature or before a live show |
| **Quick Checkpoint** | *(inline, 1 page)* | Only files changed since the last review | Optional — weekly or between major reviews |

---

## Severity Scale

Used consistently across all review tables:

| Icon | Level | Meaning |
|---|---|---|
| 🔴 | **High** | Correctness risk, agent trap, or active bug — fix before next session |
| 🟡 | **Medium** | Maintainability debt or confusing design — fix before next major feature |
| 🟢 | **Low** | Polish, dead code, minor inconsistency — fix when convenient |

---

## Standard Scoring

Code reviews score each area with ⭐ (1–5). Docs reviews score each document 1–10.
Both include an **Executive Summary table** and a **Priority Action List** at the end.

---

## Inter-Review Changelog

**`CHANGELOG.md`** is a living TODO list between review cycles.

- **Agents:** check it off as you fix items (`[ ]` → `[x]` with date)
- **New work:** log it under `### New Work` with `[+] YYYY-MM-DD — description`
- **At the next review:** the review agent reads `CHANGELOG.md` to populate the "Resolved since last review" header and then archives the current period at the bottom

---

## How to Run a New Review

### Code Review
Prompt:
```
Perform a full code audit of the Vialactée project using .agents/reviews/template_code_review.md.
Compare against the previous review at .agents/reviews/[last_code_review].md and note which
issues have been resolved. Save the result to .agents/reviews/YYYY-MM-DD_code_review.md.
```

### Docs Review
Prompt:
```
Perform a documentation audit of all .md files in the Vialactée project using
.agents/reviews/template_docs_review.md. Compare against .agents/reviews/[last_docs_review].md.
Save the result to .agents/reviews/YYYY-MM-DD_docs_review.md.
```

### Web App Review
Prompt:
```
Perform a full UI and architecture audit of wabb-interface/ using
.agents/reviews/template_webapp_review.md.

Setup:
1. Run `npm run dev` inside wabb-interface/ to start the Vite dev server (port 5173).
2. If the Python backend is needed for WS testing, start Main.py separately.
3. Open the app at http://localhost:5173, navigate every tab, and capture screenshots.

Review:
4. Follow the template structure: tab-by-tab visual tour, then architecture & code quality.
5. Capture screenshots and save them to `.agents/reviews/wapp_screenshots/` following the naming convention `YYYY-MM-DD_[tab-name].png`. Embed them using `![Alt](wapp_screenshots/YYYY-MM-DD_tab-name.png)`.
6. Compare against .agents/reviews/[last_webapp_review].md and note resolved issues.
7. Save the result to .agents/reviews/YYYY-MM-DD_webapp_review.md.

Cleanup (mandatory — run after saving the review):
8. Kill the Vite dev server: Stop-Process -Name node -ErrorAction SilentlyContinue
9. Kill any Python backend started for this session: Stop-Process -Name python -ErrorAction SilentlyContinue
9. Verify no process is still listening on port 5173 or 8080:
   netstat -ano | findstr ':5173 :8080'
```

---

## Review History

| Date | Type | Overall Health | Key Findings |
|---|---|---|---|
| 2026-05-12 | Code | ⭐⭐⭐⭐ avg | `is_song_change` never reset, `update_leds` Python loop bottleneck, no `requirements.txt` |
| 2026-05-12 | Docs | 6.2–7.1 / 10 | `PLAN.md` stale future-tense, duplicate hardware diagram, phantom modes in `modes_description.md` |
| 2026-05-12 | Web App | ⭐⭐⭐⭐ avg | Stage Architect stub, hardcoded telemetry, segment map overflow, no WS disconnect indicator |
