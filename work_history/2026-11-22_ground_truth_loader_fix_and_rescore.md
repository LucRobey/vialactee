# 2026-11-22 Ground Truth Loader Fix, Corrected References and Full Re-score

> **Date:** 2026-11-21 to 2026-11-24  
> **Session ID:** `46a56aa6-6f47-474a-a851-dd60b03410e5`  
> **Agent / Model:** Claude Sonnet 5.5, then Claude Fable 5.2  
> **Primary Goal:** Build a richer source of truth for the music analyzer; in doing so, fix a loader bug that had stretched part of the BeatNet references, correct those references, and re-score every analyzer model.  
> **Status:** COMPLETED (references corrected and re-scored, truth pipeline and review tool built; the wider plan in `research/analyzer_trials/PLAN.md` continues in later logs)  
> **Commits:** `7e334bc` (loader fix), `fd34dc3` (corrected references), `60a4f61` (trial tools), `582a00d` (plan and papers), `5724a0d` (truth pipeline and review tool), `61d9f9c` (this log) (pushed: yes)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-researcher` / `vialactee-research-manager`: assume beat F1 is the only scored signal and that the references are correct; neither says how to change or validate ground truth.

---

## 1. Context & Motivation

* The user wanted a larger, more trustworthy source of truth than the BeatNet beat files, to benchmark the real-time analyzer against and later to feed choreography research.
* A trial folder (`research/analyzer_trials/`) ran free offline tools on 20 tracks. Comparing three beat trackers there exposed that the existing BeatNet reference disagreed with the two others on several tracks.
* Owner rulings recorded during the session: AXIOM-08's ban on modifying ground truth covers normal research, not truth-building work; the audio input stays as today (5 s look-ahead).

---

## 2. Changes Made

### Benchmark engine
* **[MODIFY]** [`research/benchmarks/engine/evaluator.py`](../research/benchmarks/engine/evaluator.py):
  * `load_audio_file` returned the cached `.npz` samples (stored at 44.1 kHz) labelled with whatever `target_sr` the caller asked for. It now reads the cache's own `sr` and resamples (new helper `_resample_audio`, SciPy polyphase with a linear fallback).
  * Effect of the bug: every 22.05 kHz caller received cached tracks at half speed. That covers `extract_neural_reference.py` and `plot_beat_salience.compute_beat_importance`. Benchmark runs themselves ask for 44.1 kHz and were not affected.
* **[NEW]** [`research/tests/test_audio_loader.py`](../research/tests/test_audio_loader.py): two tests on a synthetic cached tone; the 22.05 kHz case fails on the old code (4.0 s and 220 Hz in place of 2.0 s and 440 Hz).

### Ground truth (`research/benchmarks/ground_truth/neural/`)
* **[MODIFY]** beats, downbeats and meta for 12 tracks, regenerated with BeatNet 1.1.1 on correctly loaded audio:
  * 10 whose beats ran to about twice the song length: Stayin' Alive, 01-Plastic-People, Nobody Rules the Streets, Boogie Wonderland, Roxanne, Another One Bites The Dust, September, Feeling Good, Djon maya maï, Money For Nothing_1.
  * 2 whose timestamps had been halved after a half-speed analysis, leaving beats at double tempo: Nightcall (181.8 BPM, now 90.9) and Pumped Up Kicks (260.9 BPM, now 130.4). Both are in neural-core.
* **[MODIFY]** `duration_sec` only, for Sugar and Palladium (beats were correct, recorded duration was doubled).
* **[MODIFY]** all 13 `.salience.npz` files and their `salience_data` meta block. Every one spanned twice the song length, so each beat's importance weight was read from the wrong moment of the song. This includes all 10 neural-core tracks.
* **[MODIFY]** `manifest.json`, rebuilt from the meta files on disk.
* Beats and downbeats of the other 58 tracks are byte-identical to `HEAD`. Seven of them (Bohemian Rhapsody, Flashback, Genesis, Roadgame, Sweet Child O' Mine, Under Pressure, Where Is My Mind_) have a new salience file and `salience_data` block.

### Trial tools (untracked, `research/analyzer_trials/`)
* Runners for Beat This, BeatNet, librosa, BTC chords, Demucs stems; a combined beat grid with per-beat votes; drum salience and no-beat regions; a local beat viewer; `hand_labels.json` (labels by ear on two tracks); `rescore_all.py` (scores every model against a chosen reference folder); `PLAN.md`, `FEATURE_CATALOG.md`.

### Design papers (untracked, `research/analyzer_trials/papers/`), 2026-11-23
* **[NEW]** first drafts of the four owner papers of `PLAN.md` chapter 2: `P1_source_of_truth.md` (five levels of evidence, every wanted variable with tool / check / state, truth versions, held-out tracks, licences), `P2_analyzer_contract.md` (three places for definitions / status / trust, timing classes, five status steps, shape of the graduation rule, defined and wanted signals), `P3_choreography_contract.md` (required / optional with fallback / lab-only signals, three feeds, laws / pass-fail measures / owner's choice, relation to the 48/60 rubric), `P4_how_research_runs.md` (roles, one cycle per lab, gates, logs, AXIOM-08 amendment request). `README.md` there lists the decisions asked from the owner. No threshold is fixed. Licences in P1 are from memory and unverified.
* **[MODIFY]** `tracks.json`: Nightcall note said 8.6 min, a leftover of the half-speed bug; the track lasts 4.3 min.

### Truth pipeline, automatic draft (untracked, `research/truth/`), 2026-11-23
* **[NEW]** `research/truth/build_truth.py`, `measures.py`, `meter.py`, `report.py`, `README.md`: the machine pass of the source of truth, before the owner's review. One JSON per track (`tracks/<id>.json`, 20 tracks) with a level of evidence on every value, curves at 20 Hz in a git-ignored `.npz`, and `REPORT.md`.
  * Direct measurements with no trained model: loudness, four bands, brightness, fullness, level of each stem, silence, stem presence, kick stretches, "kick leaves and returns", risers.
  * Main beats against half-beats (the merged grid is drawn at the fastest level), tempo, position in the bar from Beat This and BeatNet downbeats in blocks of 16 beats.
  * The owner's timings in `hand_labels.json` replace the machine's wherever they exist.
* **[NEW]** `research/analyzer_trials/run_adtof.py` and `vendor/ADTOF-pytorch` (cloned from github.com/xavriley/ADTOF-pytorch, source read before running): trained drum transcription, five classes, run on the mix and on the drum stem.
* **[NEW]** `research/truth/review_server.py`, `review.html`: review tool on port 8766 (launch name `truth-review`). Combined beats only, one lane per drum piece, per kind of stretch and per curve; drag, add, delete, set the "1" of the bar, undo; saves each change to `research/truth/labels/<id>.json`.
* **[NEW]** `research/truth/labels.py`: `apply_labels` (owner-placed items become H, lanes ticked "checked whole" become A) and `finalize`; called at the end of `build_truth.py`.
* **[NEW]** `research/truth/sections.py` (2026-11-24): section changes from the pipeline's own curves, compared bar by bar (8 bars each side), refined to the sharpest step and snapped to a beat, each with its reason ("kick in", "voice out", "quieter 8 dB"). Replaces the librosa novelty boundaries, which the owner judged bad; those stay in the file as `sections_old_rule`. The review page shows the reason next to each mark, and every lane explains itself on hover.
* **[NEW]** `research/tests/test_truth_pipeline.py`: 13 tests on synthetic signals, label application and section changes.
* **[NEW]** `research/analyzer_trials/VARIABLE_LIST.md`; web survey added to `FEATURE_CATALOG.md`; parked idea and techno requirement added to `PLAN.md`.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 631 passed, 5 deselected, 275 subtests passed (84 s).
* **Loader**: Nightcall loads as 258.4 s at both 44.1 kHz and 22.05 kHz (real duration 258.4 s).
* **Re-score**: `research/analyzer_trials/rescore_all.py`, all 10 models, default `RhythmConfig`, old references taken from `git archive HEAD`. No track crashed. F1@50 ms, macro:

| Model | neural-core before | after | rank | neural (70) before | after |
| :--- | ---: | ---: | :---: | ---: | ---: |
| MultiBandOnsetAudioAnalyzer | 74.5 | 80.6 | 3 → 1 | 61.1 | 71.2 |
| CostasLoopAudioAnalyzer | 71.7 | 77.5 | 4 → 2 | 59.8 | 70.3 |
| DyadicMetricalAudioAnalyzer (production) | 79.3 | 75.0 | 1 → 3 | 61.2 | 69.7 |
| DyadicWaveletAudioAnalyzer | 79.3 | 74.9 | 2 → 4 | 61.2 | 69.6 |
| SparseImpulseAudioAnalyzer | 54.0 | 58.9 | 5 → 5 | 57.7 | 68.1 |
| DualFlywheelAudioAnalyzer | 52.3 | 57.0 | 7 → 6 | 56.1 | 66.6 |
| TimbreAdaptiveAudioAnalyzer | 52.7 | 56.5 | 6 → 7 | 54.3 | 64.5 |
| PhaseInertiaAudioAnalyzer | 52.2 | 55.7 | 8 → 8 | 53.1 | 63.1 |
| AudioAnalyzer | 50.2 | 53.7 | 9 → 9 | 52.4 | 62.5 |
| DualResonatorAudioAnalyzer | 36.1 | 39.4 | 10 → 10 | 36.9 | 43.8 |

  * The "before" value for the production model (79.3) reproduces the leaderboard's 79.2.
  * On neural-core only Nightcall and Pumped Up Kicks change beat scores. Production: Nightcall 91.8 → 67.2, Pumped Up Kicks 88.6 → 69.6. MultiBandOnset: 64.0 → 93.6 and 63.4 → 94.8.
  * On the 70-track suite exactly the 12 replaced tracks change. Production on Stayin' Alive: 1.0 → 98.3.

* **Look-ahead test**: `research/analyzer_trials/rescore_lookahead.py` runs each model inside a production `Listener` (real `AudioIngestion`, stepped offline as in `tools/choreography_probe.py`) with `fakeDelay` 0.0 and 5.0, records beats at speaker time and scores them with `compute_scorecard`. Timing check on `synthetic_click_120bpm`: every beat one frame (17 ms) early in both settings, F1@50 0.975. neural-core, corrected references, F1@50 ms macro:

| Model | no look-ahead | 5 s look-ahead |
| :--- | ---: | ---: |
| MultiBandOnsetAudioAnalyzer | 83.5 | 83.2 |
| TimbreAdaptiveAudioAnalyzer | 82.9 | 82.6 |
| CostasLoopAudioAnalyzer | 83.2 | 82.1 |
| AudioAnalyzer (legacy) | 81.1 | 81.4 |
| PhaseInertiaAudioAnalyzer | 82.5 | 79.5 |
| DyadicMetricalAudioAnalyzer (production) | 78.6 | 78.1 |
| DyadicWaveletAudioAnalyzer | 78.7 | 78.0 |
| DualResonatorAudioAnalyzer | 62.0 | 67.1 |

  * Look-ahead changes beat scores by about one point or less for the leading models.
  * The production model stays about 5 points behind MultiBandOnset, again only on Nightcall (71.8 vs 95.7) and Pumped Up Kicks (74.5 vs 96.5).
  * Through the production path the legacy `AudioAnalyzer` scores 81.4, against 53.7 in the standard benchmark with its mock ingestion. Cause not investigated.
  * `DualFlywheelAudioAnalyzer` and `SparseImpulseAudioAnalyzer` crash inside `Listener` (they expect 8 bands, production gives 16).

---

## 4. Architecture Decisions & Trade-offs

* **Replace only the wrong references.** A fresh BeatNet run on this machine does not reproduce the old files on 12 healthy tracks (agreement 0.34 to 0.97; "Power" comes out at half tempo), so regenerating all 70 would have changed tracks that were not broken.
* **Re-score in the trial environment.** The project environment cannot decode tracks whose cache is missing or misnamed (see pitfalls), so the measurement used `research/analyzer_trials/.venv`, where every track loads.
* **Leaderboard untouched.** The re-score was not saved as runs; whether to add rows or re-baseline `LEADERBOARD.md` is for the owner.

---

## 5. Pitfalls & Lessons Learned

* **`extract_neural_reference.py --out-dir` is ignored.** The option is parsed and never used. A run meant for a temporary folder overwrote all 70 tracks in the official folder; the 58 unaffected tracks were restored with `git checkout`. Check where a tool writes before using `--force`.
* **A previous repair hid the bug.** Nightcall and Pumped Up Kicks had their stretched timestamps halved, which fixed the duration and left beats at double tempo. A reference that fits the song length is not thereby correct.
* **Research history was steered by these references.** Double-tempo references rewarded models that doubled the tempo, and `RESEARCH_HISTORY.md` treats Stayin' Alive as a 180° upbeat trap; on the corrected reference the production model scores 98.3% there.
* **Cache names.** `assets/musics/mp3_files/librosa/` stores apostrophes as underscores (`Sweet Child O_ Mine.mp3.npz`), while `load_audio_file` looks for the exact file name. Those tracks fall through to `torchaudio` / `librosa`, which the project environment lacks, and the run crashes on them.
* **Crashed tracks vanish from the average.** `run_benchmark.py` computes macro scores over non-crashed tracks only, so a suite can report a score over 9 tracks while listing 10.
* **The evaluator runs with `fakeDelay: 0.0`** and the bare analyzer, not through `Listener`; the leaderboard has never measured the 5 s look-ahead the installation uses.

---

## 6. Open Items & Next Steps

* [ ] Decide how to record the re-score in `LEADERBOARD.md`, `RESEARCH_HISTORY.md` and `RESEARCH_IDEA_TREE.md`, and whether the production default should change.
* [ ] Fix the cache-name lookup and the silent exclusion of crashed tracks; make `--out-dir` work or remove it.
* [ ] The six replaced tracks outside the 20 trial tracks have no second tracker to check the new BeatNet output against.
* [ ] Build the review tool: the owner must be able to correct beats, the "1", no-beat and kick stretches and drum hits in the viewer and save them.
* [ ] Add techno tracks to the 20 (owner to pick); try SongFormer for sections; write a rule for drops and build-ups.
* [ ] Owner reads the four papers in `research/analyzer_trials/papers/` and answers the decisions listed at the end of each.
* [ ] Then `PLAN.md` chapter 3: the thin slice (truth replayed into `tools/choreography_probe.py`, one clip) and the test that keeps the two labs apart.
