# [2026-11-27] Choreography lab cycle: Spectral Avalanche on the three bands (C12 second half, Avalanche_bands_mode)

> **Date:** 2026-11-27  
> **Session ID:** lab agent  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** Fourth Global Mode adapted to the analyzer's new outputs (owner: "Yes, continue"); one lab copy gated and nominated against its original.  
> **Status:** COMPLETED  
> **Commits:** none (the supervisor commits)  
> **Skills Used:** `vialactee-choreographer` (via `/light-cycle`, continued)  
> **Skill Friction:** the tool lets a lab mode be nominated against an installation mode that fails the flash rule (only lab modes are refused); the clips show the owner a strobing original. Flagged in `OWNER_QUESTIONS.md`.

---

## 1. Context & Motivation

* Second half of C12, after `Band_vu_mode` the same day.

## 2. Changes Made

* **[NEW]** `research/choreography/candidates/Avalanche_bands_mode.py`: the waterfall of Spectral Avalanche flowing at a speed set by the smoothed loudness (at most 0.45 heights a second), lit by `band_bass` low, `band_mid` in the middle, `band_high` high (each against its own recent range), flaring on a heard `kick` (while `kick_present`) at most every 0.44 s, with a white front falling from the canopy; the resting layer (waterfall and fronts) held under 7% of full light per third. A fallback for every signal.
* **[NEW]** `research/tests/test_choreography_candidate_Avalanche_bands_mode.py`: 10 tests.
* **[NEW]** `research/choreography/runs/Avalanche_bands_mode/NOTES.md`.
* **[MODIFY]** `research/choreography/BACKLOG.md`: C12 done.
* **[MODIFY]** `research/OWNER_QUESTIONS.md`: two installation modes fail the lab's flash rule.
* Written by the tools: `gates.json` (also the original's gate), `queue.json` (3 clips), `STATUS.md`, `research/INBOX.md`.

## 3. Verification & Testing

* `PY -m research.choreography.check_mode Spectral_avalanche_mode` → FAILED rule 3 (up to 19.5 flashes in one second).
* `PY -m research.choreography.check_mode Avalanche_bands_mode` → PASSED (3.0 at most; rule 4: 57% against 9% at the smallest gap; 0.58 ms a frame on this PC).
* `PY -m research.choreography.nominate Avalanche_bands_mode --against Spectral_avalanche_mode` → 3 clips; kick contrast 0.22 to 0.36 against -0.08 to 0.32.
* `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` → 231 passed, 140 subtests passed.
* `.venv/Scripts/python.exe -m research.guard check choreography` → OK.

## 4. Architecture Decisions & Trade-offs

* The flow speed no longer follows the spectral flux: that is what strobed. The pace of the avalanche now follows the loudness, and the drums show through the flare.

## 5. Pitfalls & Lessons Learned

* A falling front that is part of the flash layer makes a second flash in each third it crosses. Moving fronts belong to the capped resting layer.

## 6. Open Items & Next Steps

* [ ] The owner watches the three clips (the original strobes in them).
* [ ] The owner answers whether the two failing installation modes should be fixed in `modes/`.
* [ ] C13, C14: the cast modes and the self-detecting ones.
