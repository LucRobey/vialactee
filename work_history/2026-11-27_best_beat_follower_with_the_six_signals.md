# 2026-11-27 The Best Beat Follower With the Six Signals, and Every Analyzer Ranked on the Real Path

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** The owner asked whether the installation's analyzer is our best one, then: "could we prepare our best analyser by adding all the new variables to it?"  
> **Status:** COMPLETED (candidate built, graded, checked, proposed, then promoted on the owner's decision: `MultiBandOnsetAudioAnalyzer` is the main analyzer; not seen on the installation yet)  
> **Commits:** none yet (pushed: no)  
> **Skills Used:** `vialactee-researcher` (the cycle, run by the supervising session at the owner's request)  
> **Skill Friction:** `cycle close` wrote a proposal table whose first column was production on the check tracks only, under the heading "Production today"; fixed here. The procedure has no case for "compare two existing analyzers, nothing to tune": the open / check split then proves little, and the proposal says so.

---

## 1. Context & Motivation

The installation runs `DyadicMetricalAudioAnalyzer`. On the scoreboard its parent, `MultiBandOnsetAudioAnalyzer`, scores higher on beat and tempo, but the six signals promoted on 2026-11-27 exist on the installation's model only.

## 2. Changes Made

* **[NEW]** [`research/experiments/models/MultiBandSixSignalsAudioAnalyzer.py`](../research/experiments/models/MultiBandSixSignalsAudioAnalyzer.py): the parent model plus the six signals through the production helper `music/BandKickSignals.py`. No new rule, nothing tuned.
* **[NEW]** run folder [`research/scoreboard/runs/2026-11-27_best_beat/`](../research/scoreboard/runs/2026-11-27_best_beat/): `PLAN.md`, `OPEN.md`, `CHECK.md`, `PROPOSAL.md`, and [`ALL_MODELS.md`](../research/scoreboard/runs/2026-11-27_best_beat/ALL_MODELS.md).
* **[NEW]** [`research/tests/test_candidate_multiband_six_signals.py`](../research/tests/test_candidate_multiband_six_signals.py) (3 tests).
* **[MODIFY]** `research/scoreboard/cycle.py` (heading of the proposal table), `BACKLOG.md` (line M08), `STATUS.md`, `research/INBOX.md`.

## 3. Verification & Testing

* **The candidate against the installation's analyzer** (0 to 100):

  | | Installation | Candidate |
  |---|---|---|
  | beat, 10 open tracks | 76.2 | 76.4 |
  | beat, 10 check tracks | 80.2 | 85.0 |
  | tempo, 10 open tracks | 69.7 | 71.3 |
  | tempo, 10 check tracks | 64.2 | 77.9 |

  Gate passed on both halves; the six signals and the five signals of the `Listener` score identically.
* **The gain is three songs**: Pumped Up Kicks (beat 73 to 94, tempo 34 to 99), Nightcall (74 to 99, 29 to 100), Sweet Child O' Mine (tempo 83 to 97). On the other seventeen the two models give the same beats. Those are the songs where the installation's sub-pulse switches on.
* **Every analyzer on the real path**, for the first time (8 scored, 2 crashed on the real audio front end): see `ALL_MODELS.md`. Five are within three points on beat (78.7 to 81.5); the installation's is sixth of eight on beat (78.2) and seventh on tempo (66.9); the oldest analyzer is second (81.4).
* **Automated tests**
  ```powershell
  .venv/Scripts/python.exe -m pytest -q
  ```
  * **Result**: 832 passed, 5 deselected, 460 subtests passed (the count includes tests added by other sessions the same day).

## 4. Architecture Decisions & Trade-offs

* **A subclass of the parent, not production with its sub-pulse switched off.** It reproduces the parent's beats exactly, so its scores were known before running.
* **MultiBandOnset as the base although two older models score 0.7 higher on beat.** The differences are too small to rank, and the six signals are built on this model's kick stream and 32 bands.
* **Not promoted.** It changes what the lights do on three songs (no more half-beats), which only the owner's eye can judge.

## 5. Pitfalls & Lessons Learned

* I expected +3 on beat and +8 on tempo on the open tracks, from the 20-track averages. The open tracks gave +0.2 and +1.6: two of the three songs that carry the gain are check tracks. An average over 20 songs hid that the difference was three songs.
* The double tempo that costs most (Hotel California, Come Together, Where Is My Mind, Sucker for Pain) is shared by every model: the sub-pulse is not its cause.
* The first proposal text said no mode reads the six signals. Other sessions had put four modes that read them on the installation the same day (`0525406`); the advice on how to compare by eye was corrected.
* The research history before the scoreboard did not improve the beat on the real path: the oldest analyzer is among the best.

## 5b. Later the same day: promoted on the owner's decision

The owner: "add the six signals to MultiBandOnsetAudioAnalyzer and put it as the main".

* **[MODIFY]** [`music/MultiBandOnsetAudioAnalyzer.py`](../music/MultiBandOnsetAudioAnalyzer.py): four lines (import, creation, reset, one call per tick). The file was at 617 lines under a limit of 621 (AXIOM-07 ratchet); it is now at 621, so it cannot grow by one more line.
* **[MODIFY]** [`music/BandKickSignals.py`](../music/BandKickSignals.py): `update_from(analyzer, now, dt)` reads the values from the analyzer, which is what made four lines enough.
* **[MODIFY]** [`music/DyadicMetricalAudioAnalyzer.py`](../music/DyadicMetricalAudioAnalyzer.py): its own hook removed; it inherits the six signals (428 to 414 lines).
* **[MODIFY]** [`music/Listener.py`](../music/Listener.py): `DEFAULT_ANALYZER_MODEL = "MultiBandOnsetAudioAnalyzer"`. `config/app_config.json`: `analyzer_model` (one line, in a file that also holds the owner's own uncommitted changes).
* **[MODIFY]** `Main.py` help text, `tools/mode_studio.py`, `tools/music_studio.py` ("production" and "default" now mean the new main), `tools/choreography_probe.py` (follows the main).
* **[MODIFY]** the lab baseline (`research/scoreboard/cycle.py`, `status.py`, `compare.py`, `scoreboard.py`, `report.py`), the contract, the architecture pages, `docs/manuals/developer_tools.md`, `docs/reference/configuration_schemas.md`, the DSP and researcher skills.
* **[MODIFY]** tests: the default-model test, the governance test of the produced slots (two producing models). The candidate is an empty alias; its graded code is in the run folder.

Proof: scoreboard rebuilt with fresh recordings. The main analyzer equals the candidate on every score of the 20 tracks (0 differences); `DyadicMetricalAudioAnalyzer` equals itself before the change (0 differences). Full tests: 832 passed.

What changes on the installation: no half-beats any more on the songs where the sub-pulse switched on (among the 20: Pumped Up Kicks, Nightcall, Sweet Child O' Mine). The owner has not seen it yet. To go back: `"analyzer_model": "DyadicMetricalAudioAnalyzer"` in `config/app_config.json`.

## 6. Open Items & Next Steps

* [x] Owner: approved; promoted (section 5b).
* [ ] Owner: look at the installation with the new main analyzer, on the three songs above first.
* [ ] `music/MultiBandOnsetAudioAnalyzer.py` is at its size limit: the next change to it needs the file to be split or shortened first.
* [ ] M08 proper: the tempo level on the songs every model doubles.
* [ ] Two research models crash on the real audio front end (8 bands expected, 16 given).
