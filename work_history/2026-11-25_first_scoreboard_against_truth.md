# 2026-11-25 First Scoreboard of the Live Analyzer Against the Truth

> **Date:** 2026-11-25  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Measure, signal by signal, how far the production analyzer is from the source of truth, through the real path (production `Listener`, 5 s look-ahead).  
> **Status:** COMPLETED (first scoreboard for the two registered rhythm models on the 20 truth tracks)  
> **Commits:** `dbb65c2` (pushed: yes)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-researcher`: its benchmark commands grade beat F1 on a mock ingestion without look-ahead; nothing points to a per-signal measurement.

---

## 1. Context & Motivation

* The analyzer contract now mirrors the truth (`listener.signals`, 36 slots, log `2026-11-25_truth_mirrored_signal_contract.md`). The owner asked to go on to the next task: the scoreboard.

---

## 2. Changes Made

* **[NEW]** [`research/scoreboard/record.py`](../research/scoreboard/record.py): steps a production `Listener` offline at 60 Hz with `fakeDelay` 5.0 and records every slot of `listener.signals` at speaker time, plus candidate signals (`beat_tag`, `is_locked`, `beat_trust`, the 16 smoothed bands, the flux of the lowest band, `is_song_change`).
* **[NEW]** [`research/scoreboard/grade.py`](../research/scoreboard/grade.py): grading of moments, stretches, levels, tempo and counted values.
* **[NEW]** [`research/scoreboard/scoreboard.py`](../research/scoreboard/scoreboard.py), [`report.py`](../research/scoreboard/report.py): run, grade against `config/music_signals.json`, write [`SCOREBOARD.md`](../research/scoreboard/SCOREBOARD.md) and `scores.json`.
* **[NEW]** [`research/scoreboard/README.md`](../research/scoreboard/README.md), `.gitignore` (recordings not committed).
* **[NEW]** [`research/tests/test_scoreboard_grading.py`](../research/tests/test_scoreboard_grading.py): 10 tests on made-up signals.

No change to `music/`.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 664 passed, 5 deselected, 406 subtests passed.
* **Scoreboard** (20 tracks, averages, 0 to 100; "checked" = truth allowed to grade):

| Signal | Production (DyadicMetrical) | MultiBandOnset | Truth |
| :--- | ---: | ---: | :--- |
| beat (F1 at 50 ms) | 77 | 80 | checked |
| bpm at the right level | 67 (double 25% of the time) | 74 (double 18%) | checked |
| silence | 98 | 98 | checked |
| loudness (follows the curve) | 66 | 66 | checked |
| brightness (follows the curve) | 20 | 20 | checked |
| drop | 5 | 5 | one tool only, 6 tracks |
| section_change | never fires | never fires | one tool only |
| buildup | on 8% of the time | same | no truth yet |

* **Candidates for empty slots** (production model):

| Slot and candidate | Score | Note |
| :--- | ---: | :--- |
| band_bass, band_mid, band_high from the 16 bands | 84, 85, 74 | checked truth |
| kick from sudden rises of the lowest band | 72 | finds 93%, 64% of reports are real |
| kick from the beat tag | 69 | finds 75% |
| snare from the beat tag | 24 | one tool only |
| hat from the beat tag | 0 | one tool only |
| no_beat from "not locked" | 63 on the owner's 2 tracks, 74 on 12 | |
| section_change from the "song change" flag | 28 | one tool only |

* **Checks made on surprising results**:
  * `section_change` never firing is real, not a recording fault: on Plastic People the analyzer's verse / chorus flag is raised on 0 frames while its "song change" flag is raised 8 times inside the song.
  * Plastic People (clear 123 BPM kick) scores 60 on beats: after each break the analyzer sits at 164 BPM (four thirds of the tempo) for long stretches.

---

## 4. Architecture Decisions & Trade-offs

* **Own folder, not the old benchmark.** `research/benchmarks/` grades beat F1 on a mock ingestion without look-ahead; this measures the installation's path and every signal. The two are kept apart so old leaderboard numbers are not mixed with these.
* **Ignore zone.** An estimate that lands on a truth value not allowed to grade is ignored instead of punished, so the "checked" score does not depend on what the weak truth says.
* **Balanced score for stretches.** Plain "share of the time correct" rewards a signal stuck on the common answer.

---

## 5. Pitfalls & Lessons Learned

* **The verse / chorus flag cannot fire.** In `music/StructuralNoveltyDetector.py` the "song change" test (`asserved_novelty > 0.8`) is evaluated first and is true whenever the novelty passes its running maximum, which is the only condition of the verse / chorus branch. Every structural event is therefore reported as a song change. Not fixed here: it changes production behaviour that `transitions/` reads.
* **Tempo errors are not only double.** Seven of twenty tracks are under 50 on tempo: slow songs read at double tempo (Hotel California, Come Together, Where Is My Mind, Sucker for Pain), Nightcall and Pumped Up Kicks (double, production model only), and Plastic People at four thirds.
* **`vertical_center` is a poor stand-in for brightness** (20): it is the centre of mass over normalised band indices, not over the sound's energy.
* Beats in the truth exclude no-beat stretches; without ignoring the analyzer's beats there, 37 s of Nobody Rules the Streets counted as false alarms.

---

## 6. Open Items & Next Steps

* [ ] Owner decision: what to do first. Candidates: fill the cheap slots (four bands, kick from the low band), the tempo level, the unreachable verse / chorus flag, a better brightness.
* [ ] Owner's ear review, so that drop, section, snare, hat and no-beat lines move from "one tool only" to checked truth.
* [ ] Run the research models of `research/experiments/models/` through the scoreboard (only the two registered models were run).
