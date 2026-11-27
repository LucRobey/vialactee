# [2026-11-27] Choreography lab cycle: a Global Mode that hears the new analyzer (C10, Beat_blast_kick_mode)

> **Date:** 2026-11-27  
> **Session ID:** lab agent  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** The owner asked for ways to adapt the existing Global Modes to the analyzer's new outputs; one lab copy made, gated and nominated against its original.  
> **Status:** COMPLETED  
> **Commits:** none (the supervisor commits)  
> **Skills Used:** `vialactee-choreographer` (via `/light-cycle`)  
> **Skill Friction:** the request was not a line of the work list; added it as C10 rather than taking C02.

---

## 1. Context & Motivation

* Launch message: "find ways to adapt my existing global modes to the new outputs of the audioanalyser".
* The analyzer now produces `kick`, `kick_present`, `no_beat`, `band_bass/mid/high` (see `config/music_signals.json`).
* None of the twelve Global Modes reads `listener.signals`: they pump on the beat tracker (`beat_pulse()`,
  `is_real_beat`, `rhythm_lock`), the cast modes step on the clock of `Cast_mode_base`, the spectrum modes read
  the raw 16 bands. Survey: `research/choreography/runs/Beat_blast_kick_mode/NOTES.md`.

## 2. Changes Made

* **[NEW]** `research/choreography/candidates/Beat_blast_kick_mode.py`: a copy of `Monolithic_beat_blast_mode`
  whose rings are punched by the heard `kick` (a full punch at most every 0.46 s, the resting layer held under 7%
  of full light per third of the height), calm while `kick_present` is false or `no_beat` is true, with the ring
  brightness weighted by `band_bass` at the core, `band_mid` between, `band_high` at the rim. A fallback for every
  signal (the beat tracker, the 16 bands, the drop helper, the context energy).
* **[NEW]** `research/tests/test_choreography_candidate_Beat_blast_kick_mode.py`: 9 tests (resting light limit,
  flash ration on made-up hits up to 1200 a minute, calm in a break and on `no_beat`, the first kick after a break
  punches, empty signals, repeatability).
* **[NEW]** `research/choreography/runs/Beat_blast_kick_mode/NOTES.md`: survey of the twelve Global Modes, rounds.
* **[MODIFY]** `research/choreography/BACKLOG.md`: C10 added and done; C11 to C15 added.
* **[MODIFY]** `research/OWNER_QUESTIONS.md`: how much a break should move.
* Written by the tools: `gates.json` (also the original's gate), `queue.json` (3 clips), `STATUS.md`, `research/INBOX.md`.

## 3. Verification & Testing

* `PY -m research.choreography.check_mode Monolithic_beat_blast_mode` → **FAILED** rule 3 (3.5 flashes in one second, Nobody Rules the Streets, every feed); rule 4 not applicable (same frames on every feed).
* `PY -m research.choreography.check_mode Beat_blast_kick_mode`, round 3 → **PASSED**: 2.5 flashes a second at most; 96% to 100% of flashes on a real hit on the truth, 0% to 8% on the control; 0.86 ms a frame on this PC.
* Profile, truth / today: kick jump 18% to 32% / 18% to 30% (original 10% to 19%); light halfway up -7 to -5 ms / 11 to 14 ms; flashes in breaks 0.1 to 0.2 a second (today on Plastic People: 1.3, where today's `kick_present` says the kick is there); movement in a break 8% to 12% of normal (original 70% to 85%).
* `PY -m research.choreography.nominate Beat_blast_kick_mode --against Monolithic_beat_blast_mode` → 3 clips queued (feed today).
* `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance` → 203 passed, 140 subtests passed.
* `.venv/Scripts/python.exe -m research.guard check choreography` → OK.

## 4. Architecture Decisions & Trade-offs

* A copy in the lab, not an edit of `modes/`: the lab may not touch the installation's modes; a promotion is the owner's call after the clips.
* The ration and the resting-light limit are taken from `Kick_bands_safe_mode`, so the copy is safe by construction where the original is not.

## 5. Pitfalls & Lessons Learned

* The profile's "movement" is the swing of the total light against its half-second average: rings that drift at constant total light read as still. Making the break pulse on the beat tracker (round 2) raised movement but drew 1.3 to 1.9 visible pulses a second on beats that are not there. Dropped.
* A registered mode can go through the gate (`check_mode` accepts names from `modes/`): useful as a baseline before nominating against it.

## 6. Open Items & Next Steps

* [ ] The owner watches the three clips (`Beat_blast_kick_mode` against `Monolithic_beat_blast_mode`, today feed) and answers the break question.
* [ ] C11 to C14: the same recipe for the other Global Modes, one per cycle.
* [ ] C15: a break that moves without false pulses.
