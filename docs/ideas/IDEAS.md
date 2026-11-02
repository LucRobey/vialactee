# 💡 Vialactée — Next-Session Ideas & Personal Scratchpad (`IDEAS.md`)

> [!CAUTION]
> **AGENT INSTRUCTION — NOT SYSTEM TRUTH (TIER 4 SCRATCHPAD):**
> This file is the user's personal reminder pad and brainstorming backlog for **future sessions**.
> - **NONE of the ideas in this file are currently true or implemented in the codebase.**
> - **DO NOT cite this file as architectural truth, specification, or current behavior.**
> - **DO NOT implement anything from this file automatically** unless the user explicitly asks to work on a specific idea during a session.
> - When an idea from this file is implemented in a future session, remove or check it off here and document the actual implementation in `docs/` and `work_history/`.

---

## 🎭 Transitions & Visual Choreography Ideas

### 1. Bespoke Per-Mode Transitions (Beyond `Extending_waves_mode` Pilot)
- Give additional individual modes their own multi-stage personal transitions built around each mode's specific visual physics (following the `Extending_waves_mode` cooperative exit white-wave stacking pilot).

### 2. Mode-Coherence Engine — Remaining Extensions
Context: `partialRerollProb` (partial re-roll / micro-transitions) and `wildcardProb` (soft-rule wildcard) are now implemented in `transitions/policy.py` and `transitions/casting.py`. Remaining ideas parked for future sessions:
- **Adjacency rules:** rules about *touching* groups (e.g. "these two modes must not play on neighbouring groups"), using physical neighbours derived from the segment layout.
- **Deeper nested groupings:** groups that contain sub-groupings with their own alternatives (v1 format reserved for this, v1 itself stays 2 levels).
- **Rules that act on the grouping choice itself** (e.g. "v1 and v2 like to be together" as a rule instead of a catalogue weight).

---

## 📝 Random Notes / Future Session Reminders

- **Look at the agent conversation about the new mode.**
- *(Drop any raw thoughts, half-baked ideas, or reminders for future sessions here)*

