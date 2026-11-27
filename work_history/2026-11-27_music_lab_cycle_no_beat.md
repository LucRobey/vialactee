# 2026-11-27 Music Lab Cycle: the `no_beat` Slot (M01)

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388` (sub-agent launched with the `music-cycle` skill)  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Run one research cycle of the music lab alone, on the first open line of the work list (M01, `no_beat`).  
> **Status:** COMPLETED (candidate built, graded once on the open tracks, checked once, proposal waiting for the owner; nothing promoted, nothing committed)  
> **Commits:** `d4990e8`, committed by the supervisor together with the promotion (pushed: yes)  
> **Skills Used:** `music-cycle`, `vialactee-researcher`  
> **Skill Friction:** `vialactee-researcher`: `research.guard check music` blamed me for `research/scoreboard/README.md`, which somebody else changed at 09:40 while the cycle was running; the tuning stop rule ("two grades in a row") does not say what to do when the tuning is done offline and one grade is enough; the score of `no_beat` skips the tracks without a no-beat stretch and the procedure does not warn about it. Full list in the final report of the session.

---

## 1. Context & Motivation

* First run of the lab procedure by an agent with no help. Work list line M01: say when there is no beat to follow, so the lights stop flashing invented beats.
* Starting point: the two stand-ins of the scoreboard, "not locked" and "beat trust under 0.35": 69 and 72 on the open tracks that have a no-beat stretch, both about 2 s late.

---

## 2. Changes Made

### Candidate
* **[NEW]** [`research/experiments/models/NoBeatSlotAudioAnalyzer.py`](../research/experiments/models/NoBeatSlotAudioAnalyzer.py): production `DyadicMetricalAudioAnalyzer` plus the slot `no_beat`. Raw answer for the instant half a look-ahead behind the newest audio: no kick around it (more than 2 s between the kick before and the kick after) and tempo confidence under 0.45. The slot is the majority of the raw answers of the last 5 s, which are centred on what the speakers play. `None` until the first audio reaches the speakers. Two fixed arrays, plain numbers per tick. Reads the kicks found by `music/BandKickSignals.py` through two private fields (`_k_times`, `_k_count`).

### Run folder
* **[NEW]** [`research/scoreboard/runs/2026-11-27_no_beat/`](../research/scoreboard/runs/2026-11-27_no_beat/): `PLAN.md`, `OPEN.md`, `CHECK.md`, `PROPOSAL.md`, `run.json`, `open_scores.json`, and `tune_no_beat.py` (capture of what the analyzer knows on arrival for the ten open tracks, offline replay of the rule, sweep of the three settings).

### Lab records
* **[MODIFY]** [`research/scoreboard/BACKLOG.md`](../research/scoreboard/BACKLOG.md): M01 done (proposed); new line M11 (second pass on `no_beat`).
* **[MODIFY]** [`research/OWNER_QUESTIONS.md`](../research/OWNER_QUESTIONS.md): two questions on `no_beat` (what it should mean; two things in its grading).
* **[MODIFY]** `research/scoreboard/STATUS.md`, `research/INBOX.md`: rebuilt by the tools.
* **[NEW]** [`research/tests/test_candidate_no_beat.py`](../research/tests/test_candidate_no_beat.py): 5 tests on a synthetic song inside the `Listener` (slot empty before the speakers reach the music, values true or false, steady kick is a beat, noise without kick is no beat, production slots still written).

---

## 3. Verification & Testing

* **Command**: `research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.cycle grade 2026-11-27_no_beat --candidate NoBeatSlotAudioAnalyzer`
  * **Result**: `no_beat` 88.9 on the open tracks (six tracks graded: 89.5, 97.9, 94.5, 90.5, 83.6, 77.2); gate passed, the twelve existing signals identical. One grade only: the settings were chosen offline and the grade matched the offline replay (89.0).
* **Command**: `... cycle check 2026-11-27_no_beat --candidate NoBeatSlotAudioAnalyzer`
  * **Result**: `no_beat` 86.6 on the check tracks; gate passed. Stand-ins on the same halves, from `scores.json`: 68.6 and 72.0 (open), 79.5 and 74.8 (check).
* **Command**: `.venv/Scripts/python.exe -m pytest -q research/tests tests/governance`
  * **Result**: 179 passed, 140 subtests passed.
* **Command**: `python -m research.guard check music`
  * **Result**: **not OK**: it names `research/scoreboard/README.md`. I did not change that file; it was changed at 09:40:01 by somebody else, after my snapshot and after I had read it. Left as it is.
* **Hardware / Simulator Check**: none. Nobody has seen the signal drive a light. Cost on the Raspberry Pi not measured.

---

## 4. Architecture Decisions & Trade-offs

* **Two conditions, not one.** "No kick for 2 s" alone scores 90 but says "no beat" 35% of the time on Sucker for Pain, which keeps a pulse without kick. The tempo confidence alone scores 78 at best and fails on Plastic People, where it is lower while the kick is steady than during the breaks. Together: 89 and at most 9% of false "no beat" on the four open tracks without a no-beat stretch.
* **Confidence threshold 0.45** is a compromise between Plastic People (the only open track checked by ear, better with a high threshold) and Sucker for Pain (better with a low one).
* **Decide for "now minus half a look-ahead".** The tempo judge describes the 5 s that just arrived; taking it as the answer for their middle and voting over 5 s gives a window centred on the speakers with no extra delay line.
* **Not kept:** a third condition "onsets fell under half their usual level" (under 1 point, more false alarms).

---

## 5. Pitfalls & Lessons Learned

* The score of `no_beat` only averages tracks that have a no-beat stretch (6 of 10 on each half). False "no beat" on the others is invisible in `OPEN.md`; I measured it from the recordings.
* `OPEN.md` prints "Truth: checked" for `no_beat` although one of the six graded tracks is checked by ear; the five others are "one tool only".
* The stand-in "beat trust under 0.35" is the confidence of the 5 s before the instant; the same confidence taken 2.5 s later is already 6 points better.
* `flywheel_status` is "locked" almost all the time on the open tracks: the "not locked" stand-in is the context engine's `is_locked`, a different thing.

---

## 6. Open Items & Next Steps

* [ ] Owner: answer the proposal `research/scoreboard/runs/2026-11-27_no_beat/PROPOSAL.md` and the two `no_beat` questions.
* [ ] If approved: move the rule next to `kick_present` in `music/BandKickSignals.py` (separate change), measure the cost on the Raspberry Pi.
* [ ] M11: a regularity measure of the kick instead of the tempo confidence, once more no-beat stretches are marked by ear.
* [ ] Find out who changed `research/scoreboard/README.md` during the cycle, so the guard can be trusted again.
