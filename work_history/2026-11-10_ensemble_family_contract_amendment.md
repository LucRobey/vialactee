# 2026-11-10 Ensemble Family: Global Mode Contract Amendment

> **Date:** 2026-11-10  
> **Session ID:** `18db9bd6-5abd-4710-b19f-969e52258417`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Amend the global mode contract so Global Modes may be complex: add a third family ("ensemble") where different parts of the chandelier may follow different drivers and mechanics.  
> **Status:** COMPLETED  
> **Commits:** `d347f89` (pushed: no)  
> **Skills Used:** none (followed `.agents/skills/vialactee-project/SKILL.md` conventions by hand)  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The session started as a brainstorm of new Global Mode ideas, after reading the "Global modes redesign ideas" session ([`2026-11-10_cast_global_modes.md`](2026-11-10_cast_global_modes.md)).
* The user's own example ("the pillars are power bars in different orientations, another segment shows the high frequencies") is forbidden by the contract as written: Law 7 demands one lead driver for the whole chandelier, and Law 8.2 bans giving different drivers to different tiers.
* Four of the 13 brainstormed ideas hit that ban. The user's decision: "we should modify the contract. I want global modes to be able to do complex things."

---

## 2. Changes Made

### Contract
* **[MODIFY]** [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md):
  * The family section now lists **three** families and opens with "Global modes may be complex". It states how each family earns legibility, and that the single-driver / all-in-unison rules describe the field family, not a ceiling. Where the 2026-11-09 research document states them as universal, the contract wins.
  * **New Part B3 — Ensemble Mode Laws E1–E6** (`FAMILY = "ensemble"`):
    * E1: the part is the unit (a segment, a topology group, or a section of a segment cut at a landmark); one job per part = one driver + one mechanic.
    * E2: declared score: `PARTS` dict (part → driver) plus one docstring line per part. `LEAD` stays mandatory (driver of the parts covering the most LEDs); `SECONDARY` keeps its at-most-one limit.
    * E3: Law 7 is enforced per part (per-part mute test, same `f >= 0.30` / `g >= 0.65` thresholds); a part's job is fixed for the life of the mode.
    * E4: aliveness part by part (never fully dark or frozen while audio plays; a part may be dark by design).
    * E5: parts may react to each other, recomputed from shared signals because instances share no state; boundaries are features.
    * E6: the 2-bar spectator test applies to each part alone; no cap on the number of parts.
  * Scope notes added on Law 1, Law 7, Law 8 and Law 10.3. Law 8.2 (ban on tier driver splitting) is now explicitly a field-family rule.
  * Part C.1: states that no ensemble suite exists yet and what the first ensemble mode's test file must cover.
  * Rubric: D1 is scored per part for ensemble modes; D2 is read as "Clarity of Parts" and no longer penalizes splitting drivers across parts.
  * Attestation sentence now says "Laws 1 through 10 as scoped for its family".
* **[MODIFY]** [`docs/README.md`](../docs/README.md): the contract's one-line description mentions the three families.

### Not changed
* No code. `FAMILY` is only a class attribute; nothing in `core/`, `transitions/` or the tools branches on it.
* No ensemble mode, base class or test file exists yet.
* [`docs/research/2026-11-09_global_audio_modes_research_and_design.md`](../docs/research/2026-11-09_global_audio_modes_research_and_design.md) was left alone: it carries another session's uncommitted edit, and the contract now states which document wins.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `612 passed, 5 deselected, 265 subtests passed in 42.60s` (same pass count as before the amendment; docs link and parity checks included).
* **Hardware / Simulator Check**: not applicable (documentation only).

---

## 4. Architecture Decisions & Trade-offs

* **A third family rather than loosening Laws 7 and 8 for everyone.** The 5 field and 6 cast modes are tested against the whole-chandelier dominance check and keep passing unchanged. Complexity is opt-in by declaring `FAMILY = "ensemble"`, the same way cast was added.
* **What stays banned: several drivers on the same LEDs.** That, not tier splitting as such, is my reading of why `Architectural_drum_mode` was unreadable (three mechanics, each further modulated by `beat_tag`, `spectral_tilt` and `vertical_center`). This is an interpretation, not a measured result.
* **`LEAD` kept mandatory.** `tests/test_mode_helpers.py::test_lead_tags_match_implementation_code_ast` and the transition policy need one `lead:` tag per registered mode.
* **No cap on parts or jobs.** The user asked for freedom; the only structural limit is "one line per job" (E2 / E6).

---

## 5. Pitfalls & Lessons Learned

* The choreography governance tests (`tests/governance/test_mode_choreography*.py`) iterate `standard_modes` only. Global modes are covered by per-family files with hardcoded spec lists, so a new family needs its own file.
* `work_history/README.md` and the research document both carry uncommitted edits from the HUD-split session. Committing this session's work needs care not to sweep those in.

---

## 6. Open Items & Next Steps

* [ ] Build the first ensemble mode (candidates from the brainstorm: Stalagmites & Stalactites, Four Voices, Snapshot, Dashboard) with a shared `Ensemble_mode_base` if two modes need the same part resolution.
* [ ] Write the per-part mute harness (Law E3): `tools/choreography_matrix.py` measures the whole strip today; it needs a per-part LED mask.
* [ ] Pillar sections cut at rung altitudes (needed by the "Windows" idea) have no helper yet; `SegmentSpatialProfile.split_1` / `split_2` are plain thirds.
* [ ] Commit this session (contract, `docs/README.md`, this log, and this session's row in `work_history/README.md`).
