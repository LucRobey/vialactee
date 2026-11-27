# [2026-11-27] Choreography lab cycle: Concentric Radial Ripple on the heard kick (C11, Ripple_kick_mode)

> **Date:** 2026-11-27  
> **Session ID:** lab agent  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** Second Global Mode adapted to the analyzer's new outputs (owner's request of C10); one lab copy gated and nominated against its original.  
> **Status:** COMPLETED  
> **Commits:** none (the supervisor commits)  
> **Skills Used:** `vialactee-choreographer` (via `/light-cycle`, continued)  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The owner said "continue" after the C10 cycle (`2026-11-27_choreography_lab_cycle_beat_blast_kick.md`); C11 is the next Global Mode of that plan.

## 2. Changes Made

* **[NEW]** `research/choreography/candidates/Ripple_kick_mode.py`: a copy of `Concentric_radial_ripple_mode`. A heard `kick` throws one violet ring from the core (0.6 s to the rim); a white heart (radius 0.40) on top, at most every 0.44 s and only while the kick is present; while `kick_present` is false or `no_beat` true, only the original's three steady rings drift, at the speed of the loudness and a constant brightness; `band_bass` glows at the core, `band_high` at the rim. A fallback for every signal.
* **[NEW]** `research/tests/test_choreography_candidate_Ripple_kick_mode.py`: 10 tests (no flash without kicks, fast hits up to 1200 a minute, 25 runs of random irregular hits, steady kick visible, calm in breaks and on `no_beat`, first kick after a break, empty signals, repeatability).
* **[NEW]** `research/choreography/runs/Ripple_kick_mode/NOTES.md`: rounds and numbers.
* **[MODIFY]** `research/choreography/BACKLOG.md`: C11 done; a finding added to C07.
* Written by the tools: `gates.json` (also the original's gate), `queue.json` (3 clips), `STATUS.md`, `research/INBOX.md`.

## 3. Verification & Testing

* `PY -m research.choreography.check_mode Concentric_radial_ripple_mode` → PASSED (no large flash; rule 4 not applicable).
* `PY -m research.choreography.check_mode Ripple_kick_mode`, round 3 → PASSED: 3.0 flashes a second at most (Nobody Rules the Streets, at the limit); 100% of flashes on a real hit on the truth, 0% to 5% on the control; 0.90 ms a frame on this PC.
* Profile, truth / today: kick jump 9% to 16% / 8% to 13%; flashes on a real hit 100% / 75% to 100%; pulses in breaks 0.0 to 0.1 (today on Plastic People 0.7); movement in a break 35% to 41% / 29% to 58% of normal.
* `PY -m research.choreography.nominate Ripple_kick_mode --against Concentric_radial_ripple_mode` → 3 clips; kick punch contrast 0.14 to 0.20 against 0.15.
* `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` → 213 passed, 140 subtests passed.
* `.venv/Scripts/python.exe -m research.guard check choreography` → OK.

## 4. Architecture Decisions & Trade-offs

* The violet of the original is kept (its identity); the punch is carried by a white heart, because a violet ring gives little light and cannot make a kick seen.
* Ration 0.44 s, not 0.46 s: see section 5.

## 5. Pitfalls & Lessons Learned

* A ration of 0.46 s refuses some kicks of a steady 128-a-minute track (0.469 s apart, sometimes 27 frames = 0.45 s at 60 frames a second). Seen on the time strip as a missing heart every few seconds. Noted under C07.
* The profile measures by height: a mode that places bass and treble by distance from the centre gets "bottom follows bass" near 0 whatever it does.

## 6. Open Items & Next Steps

* [ ] The owner watches the three clips against Concentric Radial Ripple.
* [ ] C12 to C14: the other Global Modes.
