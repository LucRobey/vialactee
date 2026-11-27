# 2026-11-27 Music Lab Pilot Cycle: Three Band Levels and a First Kick

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Run one research cycle of the music lab by hand, end to end, to find out what the lab still lacks, and fill the cheap slots the scoreboard pointed at.  
> **Status:** COMPLETED (candidate built, tuned on half the tracks, scored on all 20, gate passed, proposal written; nothing promoted)  
> **Commits:** `b516564` (pushed: no)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-researcher`: describes a six-step loop that ends on beat F1 in the old benchmark; none of this cycle's steps (fill a slot, tune on open tracks, per-signal gate, proposal) is in it.

---

## 1. Context & Motivation

* The scoreboard (`work_history/2026-11-25_first_scoreboard_against_truth.md`) showed three band levels and a kick within reach of existing signals. The owner chose a pilot cycle on them.

---

## 2. Changes Made

### Lab tools (`research/scoreboard/`)
* **[MODIFY]** `scoreboard.py`: any model can be run, production or candidate from `research/experiments/models/` (`load_model_class`); `--out` writes a run into its own folder; frame time kept per track.
* **[MODIFY]** `record.py`: measures the time of the whole listener step per tick.
* **[NEW]** [`research/scoreboard/compare.py`](../research/scoreboard/compare.py): before and after of two models of one run. The gate (no signal the baseline produces loses more than 1 point on average; tracks losing more than 5 points are listed), the new signals scored apart on open and check tracks, the cost per tick.
* **[NEW]** [`research/tests/test_scoreboard_compare.py`](../research/tests/test_scoreboard_compare.py): 8 tests (gate cases; the candidate inside the `Listener` on a synthetic song: empty slots before the speakers reach the music, kicks at speaker time, `kick_present` on and off, levels within 0..1).

### Candidate
* **[NEW]** [`research/experiments/models/BandKickSlotsAudioAnalyzer.py`](../research/experiments/models/BandKickSlotsAudioAnalyzer.py): production `DyadicMetricalAudioAnalyzer` plus five slots: `band_bass`, `band_mid`, `band_high` (the 32-band spectrum summed in three ranges, in dB under a slowly falling ceiling), `kick` (peaks of the parent's kick stream) and `kick_present` (a kick in the last 2 s and another in the next 2 s, which the look-ahead makes knowable). Values are measured on arrival and written to the slots through a delay line when the speakers reach them.

### Run folder `research/scoreboard/runs/2026-11-27_bands_kick/`
* **[NEW]** `tune_kick.py` (capture of the band rises on the 10 open tracks, offline sweep of the detector settings), `SCOREBOARD.md`, `scores.json`, `COMPARISON.md`, `PROPOSAL.md`.

### Registry
* **[MODIFY]** `research/experiments/LEADERBOARD.md` and **[NEW]** `research/experiments/runs/RUN_20261127_005526_BandKickSlotsAudioAnalyzer_pilot_bands_kick_synth/`: the synthetic run of the candidate, as AXIOM-08 requires.

No change to `music/`.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 672 passed, 5 deselected, 406 subtests passed.
* **Scoreboard, 20 tracks, candidate against production** (`COMPARISON.md`):

| Signal | Open tracks (10) | Check tracks (10) | All | Truth |
| :--- | ---: | ---: | ---: | :--- |
| kick | 75.2 | 84.7 | 79.9 | checked |
| kick_present | 81.0 | 89.1 | 85.0 | checked |
| band_bass | 81.9 | 83.8 | 82.8 | checked |
| band_mid | 89.0 | 88.2 | 88.6 | checked |
| band_high | 92.6 | 94.3 | 93.4 | checked |

  * Gate passed: beat, bpm, drop, section_change, silence, loudness and brightness are identical to the point.
  * Kick: finds 85% of the truth kicks, 79% of its reports are real, 21 ms late.
  * Cost: 0.491 ms to 0.533 ms per tick for the whole listener step on this PC (measured with 5 runs in parallel, so noisy).
* **Kick tuning** on the open tracks only (`tune_kick.py sweep`): F1 64.0 with the first settings (finds 95%, 50% real), 76.7 with the chosen ones (over average 4.0, share of peak 0.5, low share 0.25). A snare test added nothing and was dropped.
* **Old regression rule**: `python -m research.benchmarks.run_benchmark --suite synthetic`: 96.2% F1@50 ms for production and for the candidate; 0.21 and 0.22 ms per frame.

---

## 4. Architecture Decisions & Trade-offs

* **Subclass production, add only.** The candidate cannot change a signal it does not touch, which makes the gate trivially true here; the gate was still built and run because the next candidates will not be so harmless.
* **Tune offline on a capture.** One listener run per open track stores the band rises; the detector rule is then replayed in a loop for 200 settings in a minute instead of 200 listener runs.
* **Open and check tracks.** The owner has not fixed the held-out list, so the pilot used odd ids to tune and even ids to check. Scores were higher on the check half, so the tuning did not overfit.
* **The band levels come from the 32-band spectrum, not the 16-band one.** Grouping the 16 visual bands scored 84 / 85 / 74; the 32 bands score 83 / 89 / 93.

---

## 5. Pitfalls & Lessons Learned (what the pilot says about the lab)

* **The old benchmark logs a crashed candidate as a 0.0% row.** Its mock front end has no 32-band spectrum; the candidate crashed on every track and `--save-run` still wrote a line in `LEADERBOARD.md`. The line and its run folder were removed, the candidate was given the parent's fallback, and the run was redone.
* **`LEADERBOARD.md` has no place for a signal other than the beat.** The per-signal record of a run lives in `research/scoreboard/runs/<run>/`; the two registries are not linked.
* **The cost is measured on a PC under load.** A quiet single run, and the Raspberry Pi, are still missing; so is a memory test of the candidate's update.
* **The kick truth is a model's opinion.** It is level M2 (drum model agreeing with a measured low thump), but the model was trained on rock and pop; the weakest tracks are electronic (Genesis 49, Roadgame 60).
* **`band_sub` cannot be filled from the front end as it is**: its lowest band is centred near 100 Hz.

---

## 6. Open Items & Next Steps

* [ ] Owner: read `research/scoreboard/runs/2026-11-27_bands_kick/PROPOSAL.md`; decide whether the five signals go into the production analyzer.
* [ ] Show the kick driving a light (the thin slice of the choreography lab) before any trust level is set.
* [ ] Lab: fix the held-out list; a per-signal leaderboard; make the old benchmark refuse to log a crashed run; a quiet timing run and a memory test for candidates; rewrite the research skills around this cycle.
* [ ] Next candidates the scoreboard points at: the tempo level (double tempo 25% of the time), the unreachable verse / chorus flag, brightness, `no_beat`.
