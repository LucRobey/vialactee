# Vialactée — Web App Review — YYYY-MM-DD

> **Type:** Web App / UI Audit
> **Stack:** <!-- e.g. React 19 + TypeScript + Vite 8 -->
> **Running at:** <!-- e.g. http://localhost:5173/ -->
> **Reviewer:** <!-- Antigravity / manual / name -->
> **Previous review:** <!-- link to previous file, or N/A -->
> **Resolved since last review:** <!-- list items from previous Priority Action List that are now closed -->

---

## Executive Summary

<!-- 2–3 sentence overall verdict. What is the app's current functional state? What are the top 3 risks? -->

---

## Visual Tour

<!-- One section per tab / major page. Capture screenshots and save them to `.agents/reviews/wapp_screenshots/YYYY-MM-DD_[tab-name].png`. Embed them here. -->

### Tab 1 — [Tab Name]

<!-- ![Tab Name](wapp_screenshots/YYYY-MM-DD_tab-name.png) -->

**Rating: X / 10**

What's working:
- <!-- item -->

**Issues found:**
1. <!-- issue — Severity: HIGH / MEDIUM / LOW -->

---

### Tab 2 — [Tab Name]

**Rating: X / 10 — [PLACEHOLDER / WIP / COMPLETE]**

<!-- description -->

**Issues found:**
1. <!-- issue -->

---

### Tab 3 — [Tab Name]

**Rating: X / 10**

What's working:
- <!-- item -->

**Issues found:**
1. <!-- issue -->

---

### Tab 4 — [Tab Name]

**Rating: X / 10**

What's working:
- <!-- item -->

**Issues found:**
1. <!-- issue -->

---

### Tab 5 — [Tab Name]

**Rating: X / 10**

What's working:
- <!-- item -->

**Issues found:**
1. <!-- issue -->

---

## Architecture & Code Quality

### `[file].ts` — [Role]

**Strengths:**
- <!-- strength -->

**Issues:**
1. <!-- issue -->

---

### `[file].ts` — [Role]

**Strengths:**
- <!-- strength -->

**Issues:**
1. <!-- issue -->

---

### `[Component].tsx` — [Role]

**Strengths:**
- <!-- strength -->

**Issues:**
1. <!-- issue -->

---

## Prioritized Findings

| # | Issue | Severity | Page | Type |
|---|---|---|---|---|
| 1 | <!-- issue --> | **HIGH** | <!-- page --> | <!-- Feature gap / UX / Bug / Architecture / Maintainability / Type safety / Performance / Code quality --> |
| 2 | <!-- issue --> | MEDIUM | <!-- page --> | |
| 3 | <!-- issue --> | LOW | <!-- page --> | |

---

## Recommendations (Ordered by Priority)

### Immediate
1. <!-- item -->

### Short Term
2. <!-- item -->

### Long Term
3. <!-- item -->

---

## CSS / Styling Notes

<!-- File sizes, global vs scoped, animation patterns, design system health. -->

---

## ⚠️ Mandatory Cleanup — Run After Saving the Review

> This section must be executed by the agent at the end of every web app review session,
> regardless of whether the review completed fully.

```powershell
# 1. Kill the Vite dev server (node process on port 5173)
Stop-Process -Name node -ErrorAction SilentlyContinue

# 2. Kill any Python backend started for this session
Stop-Process -Name python -ErrorAction SilentlyContinue

# 3. Verify ports are free (output should be empty)
netstat -ano | findstr ":5173 :8080"
```

**Do not skip this step.** Leaving the Vite server running blocks future `npm run dev` restarts and wastes system memory during audio/LED processing sessions.
