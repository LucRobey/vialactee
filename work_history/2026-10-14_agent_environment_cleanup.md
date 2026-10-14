# 2026-10-14 Agent Environment Cleanup (budget reconciliation, AGENT.md, researcher skill split)

> **Date:** 2026-10-14  
> **Session ID:** `ceac1684-8e77-4719-a815-04336e421601`  
> **Agent / Model:** Antigravity (Claude Sonnet)  
> **Primary Goal:** Remove contradictions and bloat from the agent environment (`.agents/`) so agents get one consistent, navigable context.  
> **Status:** COMPLETED (uncommitted; the tree also holds unrelated in-flight work from the user)  
> **Commits:** none yet (pushed: no)

---

## 1. Context & Motivation

An audit of `.agents/` found: (a) a frame-budget contradiction (CONSTITUTION/AXIOM-01 say 30 FPS / 20 ms; research skills said 60 FPS / 16.6 ms), (b) a stale 92-line `AGENT.md` that duplicated the project skill and carried a changelog, (c) a 28 KB researcher skill, (d) `vialactee-hardware-deploy` never being registered as a skill.

---

## 2. Changes Made

### Budget reconciliation (canonical: AXIOM-01)
* **Rule adopted:** LEDs render at **30 FPS** (33.33 ms, <= 20 ms compute). The audio analyzer **ticks at 60 Hz** (AXIOM-01 section 1.4). The research gate of <= 3.0 ms is **per `update()` tick**.
* **MODIFY** `.agents/skills/vialactee-researcher/SKILL.md`, `.agents/skills/vialactee-research-manager/SKILL.md`, `research/docs/templates/RESEARCH_CYCLE_ARTIFACT_TEMPLATE.md`, `research/README.md`.

### AGENT.md
* **MODIFY** `.agents/AGENT.md`: reduced to a pointer (read order, source-of-truth table, skill index, session checklist).
* **NEW** `docs/archive/AGENT_context_snapshot_2026-10-14.md`: verbatim previous content (Tier 4 archive), including the "Recent Upgrades" list.

### Researcher skill split
* **MODIFY** `.agents/skills/vialactee-researcher/SKILL.md` (28 KB -> about 16 KB): core loop plus a references index.
* **NEW** `.agents/skills/vialactee-researcher/references/`: `redesign_playbook.md`, `subagent_delegation.md`, `executive_report_template.md`, `scorecard_and_guardrails.md` (content moved verbatim; hardcoded SOTA now flagged as a snapshot, `LEADERBOARD.md` is the authority).
* Removed the unverified "9-track" count that contradicted the 10-track suite.

### hardware-deploy skill
* **MODIFY** `.agents/skills/vialactee-hardware-deploy/SKILL.md`: **root cause** was unquoted YAML in the `description` (`full: 1,304 LEDs` contains `: `, an invalid plain scalar). Description is now quoted; all 7 skills parse (checked with PyYAML).

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q tests/governance` -> `24 passed in 7.96s`.
* PyYAML frontmatter parse of all `.agents/skills/*/SKILL.md` -> 7 OK.
* The full suite was not run (docs/skills-only change).

---

## 4. Architecture Decisions & Trade-offs

* Snapshot archived in `docs/archive/` (existing Tier 4 convention) rather than `work_history/`, which holds dated session logs, not reference snapshots.
* The <= 3.0 ms research gate was kept per tick (historical benchmarks stay comparable) even though AXIOM-01 allots <= 3.5 ms of audio DSP per 30 FPS frame (= 2 ticks). Safe today (models run about 0.5 ms/tick) but not strictly consistent; see open items.

---

## 5. Pitfalls & Lessons Learned

* Colons followed by a space in unquoted YAML frontmatter silently drop a skill. Always quote `description:` values.
* Remaining "60 FPS" strings live in Python docstrings/comments (`research/experiments/models/*`, `tools/*studio.py`), `generate_pdf.py` marketing text and `tests/test_benchmark_engine.py` ("16.6ms"). They were left untouched (code, not agent context).

---

## 6. Open Items & Next Steps

* [ ] Decide whether the research gate should become 1.5 ms per tick (so two ticks fit AXIOM-01's 3.5 ms) or the axiom allotment should be restated per tick.
* [ ] Decide whether `.agents/docs/` (historical) should move to `docs/archive/`.
* [ ] Add a governance test that validates skill frontmatter and that doc budget numbers match AXIOM-01.
* [ ] Reload the IDE/agent session and confirm `vialactee-hardware-deploy` now appears.
