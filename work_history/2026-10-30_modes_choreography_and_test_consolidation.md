# [2026-10-30] Opposite Sides Rework, Law 7 Batches 1–4 Promotion & Test Suite Consolidation

> **Date:** 2026-10-30  
> **Session ID:** `2edcb22` / `a7b4c62` (retroactive log added 2026-11-02)  
> **Agent / Model:** Antigravity / User  
> **Primary Goal:** Rework `Opposite_sides_mode` (bass-vs-treble VU tug-of-war + 1-LED firework crackle), align the remaining 5 modes (`Rainbow`, `Proportion_rainbow`, `Middle_bar`, `Chromatic_chaser`, `Extending_waves`) to pass `CONFORMING_MODES_PHASE_4A`, and consolidate legacy root test modules into `tests/governance/` and `tests/transitions/`.  
> **Status:** COMPLETED  
> **Commits:** `2edcb22` `a7b4c62` `25b75ce` (pushed: yes)  
> **Skills Used:** `vialactee-project`, `vialactee-mode-creator`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* Complete the formal promotion of all 13 registered modes into `CONFORMING_MODES_PHASE_4A` in [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py).
* Rework [`modes/Opposite_sides_mode.py`](../modes/Opposite_sides_mode.py) into a bass-vs-treble VU tug-of-war around a fixed 8% core with 1-LED pinpoint sparks.
* Remove duplicate root-level governance and transition test files (`tests/test_code_governance.py`, `tests/test_docs_parity_and_bugs.py`, `tests/test_transitions_manager_and_dna.py`) in favor of `tests/governance/` and `tests/transitions/`.

---

## 2. Changes Made

### Mode Rework & Law 7 Alignment (`2edcb22`)
* **[MODIFY]** [`modes/Opposite_sides_mode.py`](../modes/Opposite_sides_mode.py) & **[NEW]** [`tests/test_opposite_sides_mode.py`](../tests/test_opposite_sides_mode.py):
  * Implemented slow-peak AGC per-wing normalization, `spectral_tilt` competitive push, anti-aliased fractional coverage around a fixed 8% center core, and a 64-entry golden-ratio 1-LED pinpoint spark table (`_spawn_tbl`, `_stagger_tbl`, `_crackle_queue`).
* **[MODIFY]** [`modes/Rainbow_mode.py`](../modes/Rainbow_mode.py) & [`modes/Proportion_rainbow_mode.py`](../modes/Proportion_rainbow_mode.py):
  * Removed the competing `beat` brightness multiplier so `spectrum` (`asserved_fft_band` / `band_proportion`) is the undisputed lead driver.
* **[MODIFY]** [`modes/Middle_bar_mode.py`](../modes/Middle_bar_mode.py):
  * Driven bar width by `self.beat_pulse()` (`LEAD = "beat"`) and outer 2-LED cap tinting by low-band energy (`SECONDARY = ("spectrum",)`).
* **[MODIFY]** [`modes/Chromatic_chaser_mode.py`](../modes/Chromatic_chaser_mode.py):
  * Added beat-pulse velocity surge (`0.9 + 0.5 * pulse`) and brightness modulation (`LEAD = "beat"`) plus an energy-scaled ahead spark halo (`SECONDARY = ("level",)`).
* **[MODIFY]** [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py):
  * Added `ctx.energy`-scaled outward flow speed (`flow_gain`), wave amplitude, and center-outward level bed glow (`LEAD = "level"`), with `beat_pulse()` crest shimmer (`SECONDARY = ("beat",)`).
* **[MODIFY]** [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md):
  * Synchronized Lead/Secondary columns and mode descriptions with the updated implementations.

### Test Consolidation & Choreography Promotion (`a7b4c62`)
* **[MODIFY]** [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py):
  * Promoted all 13 registered modes into `CONFORMING_MODES_PHASE_4A`.
* **[DELETE]** `tests/test_code_governance.py`, `tests/test_docs_parity_and_bugs.py`, `tools/test_udp.py` (consolidated into `tests/governance/` and existing unit test modules).
* **[RENAME]** `tests/test_transitions_manager_and_dna.py` -> `tests/transitions/test_manager_and_dna.py` (subsequently renamed to `tests/transitions/test_manager.py` in `ba95931`).

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: All unit and governance tests pass (`13/13` modes in `CONFORMING_MODES_PHASE_4A`).

---

## 4. Open Items & Next Steps

* [ ] Audit real-audio choreography metrics (`--track`) and visual quality of the 5 aligned modes (`Chromatic_chaser_mode` still retains `R_std(-all) = 19.3` from constant-speed sweeping; `Extending_waves_mode` still spawns waves on `is_tick`; `Bary_rainbow_mode` has competing `level`/`beat` brightness).
