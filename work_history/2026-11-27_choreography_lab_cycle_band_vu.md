# [2026-11-27] Choreography lab cycle: Architectural VU Equalizer on the three bands (C12, Band_vu_mode)

> **Date:** 2026-11-27  
> **Session ID:** lab agent  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** Third Global Mode adapted to the analyzer's new outputs (owner: "Yes, run C12"); one lab copy gated and nominated against its original.  
> **Status:** COMPLETED (C12 half done: Spectral Avalanche still open)  
> **Commits:** none (the supervisor commits)  
> **Skills Used:** `vialactee-choreographer` (via `/light-cycle`, continued)  
> **Skill Friction:** none

---

## 1. Context & Motivation

* Follows the C10 and C11 cycles of the same day. C12 named two modes; one cycle = one mode, so the VU Equalizer was done and Spectral Avalanche left open.

## 2. Changes Made

* **[NEW]** `research/choreography/candidates/Band_vu_mode.py`: three auto-ranging meters placed on the building (bass: outer pillars and low bridges, red; middle: inner pillars and middle bridges, amber; treble: canopy, cool white). A heard `kick` (while `kick_present`) punches the whole bass meter in a white-tinted flash at most every 0.44 s, a white cap otherwise. A meter falls at most 0.9 of its height a second. A fallback for every signal.
* **[NEW]** `research/tests/test_choreography_candidate_Band_vu_mode.py`: 8 tests (level jumps at 1.5 to 15 a second, 20 runs of random levels with irregular kicks, the punch on the bass meter only, the cap for a kick too soon, no punch while the kick is away, bass and treble in their places, empty signals, repeatability).
* **[NEW]** `research/choreography/runs/Band_vu_mode/NOTES.md`.
* **[MODIFY]** `research/choreography/BACKLOG.md`: C12 half done.
* Written by the tools: `gates.json` (also the original's gate), `queue.json` (3 clips), `STATUS.md`, `research/INBOX.md`.

## 3. Verification & Testing

* `PY -m research.choreography.check_mode Architectural_vu_equalizer_mode` → PASSED (3.0 flashes a second at most; rule 4 not applicable).
* `PY -m research.choreography.check_mode Band_vu_mode`: round 1 FAILED rule 4; rounds 2 to 4 PASSED. Round 4: 2.5 flashes a second at most; 92% of flashes on a real hit on the truth, 30% on the control (smallest gap); 0.27 ms a frame on this PC.
* Profile, truth / today (round 4): kick jump 12% to 29% / 13% to 29%; flashes on a real hit 82% to 92% / 73% to 86%; top follows treble 0.42 to 0.64 / 0.46 to 0.65; bottom follows bass 0.17 to 0.74 / 0.07 to 0.73.
* `PY -m research.choreography.nominate Band_vu_mode --against Architectural_vu_equalizer_mode` → 3 clips; kick contrast 0.22 to 0.25 against 0.09 to 0.19.
* `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` → 221 passed, 140 subtests passed.
* `.venv/Scripts/python.exe -m research.guard check choreography` → OK.

## 4. Architecture Decisions & Trade-offs

* A level-led mode needs a real flash on the kick to pass "follows the music": a thin cap is safe but invisible to the gate and almost to the eye.
* Auto-ranging meters: they use their whole height on any song, at the cost of a little more movement in breaks (the range narrows when the music is quiet, down to a span of 0.25).

## 5. Pitfalls & Lessons Learned

* The lab names segments "Segment v1", not "v1".
* The pillars do not span the whole height (v1: 0.23 to 0.93; v3: 0.0 to 0.7): a meter on altitude alone could never fill v3 or empty v1.

## 6. Open Items & Next Steps

* [ ] The owner watches the three clips against Architectural VU Equalizer.
* [ ] C12, second half: Spectral Avalanche. Then C13, C14.
