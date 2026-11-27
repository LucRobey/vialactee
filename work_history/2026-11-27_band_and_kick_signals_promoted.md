# 2026-11-27 Band Levels and Kick Promoted to the Production Analyzer

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Carry out the owner's approval of the pilot proposal: put the five new signals (`band_bass`, `band_mid`, `band_high`, `kick`, `kick_present`) into the analyzer that runs on the installation.  
> **Status:** COMPLETED (promoted, scores identical to the candidate's, tests pass; not rated by the owner, no mode reads them, cost on the Raspberry Pi not measured)  
> **Commits:** see `git log` for this date (pushed: no)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-researcher` / `vialactee-research-manager`: describe promotion as replacing `music/AudioAnalyzer.py` after a beat-F1 run; nothing covers "a candidate that adds slots is promoted as a helper file, the list of produced slots is updated in four places, and the candidate becomes an alias".

---

## 1. Context & Motivation

The pilot cycle of the music lab ([log](2026-11-27_music_lab_pilot_cycle_bands_and_kick.md)) ended with a proposal to the owner: [`PROPOSAL.md`](../research/scoreboard/runs/2026-11-27_bands_kick/PROPOSAL.md). On 2026-11-27, after trying fixes A and B on the installation ("everything looks good"), the owner approved it. This is the first promotion from the new lab, so it also sets how a promotion is done.

## 2. Changes Made

### Production (`music/`)
* **[NEW]** [`music/BandKickSignals.py`](../music/BandKickSignals.py) (157 lines): the candidate's measurement as a helper class, `BandKickSignals(nb_bands, lookahead_seconds)` with `update(now, dt, bands, kick_stream, low_rise, signals)` and `reset()`. Same constants and same logic as the candidate; the only change is that it receives the analyzer's values as arguments instead of reading them from `self`.
* **[MODIFY]** [`music/DyadicMetricalAudioAnalyzer.py`](../music/DyadicMetricalAudioAnalyzer.py) (414 to 427 lines): creates the helper, resets it, and calls it at the end of `detect_band_peaks`. Nothing else in the rhythm code is touched. `MultiBandOnsetAudioAnalyzer.py` was not an option: it is over the 500-line cap and may not be modified without being split.
* **[MODIFY]** [`music/MusicSignals.py`](../music/MusicSignals.py): `PRODUCED`, the list of slots the production analyzer writes itself.

### Contract
* **[MODIFY]** [`config/music_signals.json`](../config/music_signals.json): new status `produced`; the five signals carry it, with source `BandKickSignals.update`.
* **[MODIFY]** [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md): section 6, the five rows read PRODUCED, and rule 4 says who writes them and that they stay `None` until the first audio has reached the speakers.
* **[MODIFY]** [`docs/architecture/audio_pipeline.md`](../docs/architecture/audio_pipeline.md): the new file in the file table.

### Lab
* **[MODIFY]** [`research/experiments/models/BandKickSlotsAudioAnalyzer.py`](../research/experiments/models/BandKickSlotsAudioAnalyzer.py): now an empty subclass of the production model, kept so that past records can be replayed by name. The graded code is in git (`b516564`).
* **[MODIFY]** [`research/scoreboard/SCOREBOARD.md`](../research/scoreboard/SCOREBOARD.md) and `scores.json`: rebuilt; the production model now produces 13 signals.
* **[MODIFY]** [`PROPOSAL.md`](../research/scoreboard/runs/2026-11-27_bands_kick/PROPOSAL.md): the decision at the top.

### Tests
* **[NEW]** [`tests/test_band_kick_signals.py`](../tests/test_band_kick_signals.py) (8 tests): the slots wait for the speakers, a kick comes out look-ahead seconds after it was heard, `kick_present` needs a kick before and after, a peak without low band is not a kick, levels, reset, and a memory test (a tick allocates nothing).
* **[MODIFY]** [`tests/governance/test_music_signals_contract.py`](../tests/governance/test_music_signals_contract.py): `PRODUCED` must equal the `produced` entries of the signal list; the default model fills the produced slots and the other models leave them empty; the "a written slot is seen" test now uses two slots that are still empty.

## 3. Verification & Testing

* **Same scores as the candidate.** The production model was scored on the 20 truth tracks and compared, value by value, with the candidate's scores of the pilot (`runs/2026-11-27_bands_kick/scores.json`): every score of every signal on every track is identical. Only the measured time per tick differs.
  ```powershell
  research/analyzer_trials/.venv/Scripts/python.exe -m research.scoreboard.scoreboard
  ```

  | Signal | Before | Now |
  |---|---|---|
  | `kick` | empty | 80 |
  | `kick_present` | empty | 85 |
  | `band_bass` / `band_mid` / `band_high` | empty | 83 / 89 / 93 |
  | beat, tempo, silence, loudness, brightness, drop, section change | 77, 67, 98, 66, 20, 5, never | unchanged |

* **Automated tests**
  ```powershell
  .venv/Scripts/python.exe -m pytest -q
  ```
  * **Result**: 727 passed, 5 deselected, 412 subtests passed (718 before).
* **Cost per tick on this PC**: 0.58 ms for the whole listener step in this run (0.53 ms for the candidate in the pilot, measured before fix B added its own small work and on a different run; the two are not a clean comparison). The budget is 16.7 ms.

## 4. Architecture Decisions & Trade-offs

* **A helper file, not a subclass.** The production default stays `DyadicMetricalAudioAnalyzer`; no registry entry, no config change, nothing to switch on the installation.
* **Only the default model produces the slots.** `AudioAnalyzer` and `MultiBandOnsetAudioAnalyzer` leave them empty; the governance test says so.
* **`None` for the first look-ahead seconds.** After a start or a reset nothing has reached the speakers yet, so the five slots answer `None` ("does not know") for 5 seconds, as the contract allows.
* **The candidate becomes an alias** instead of being deleted, so run records, the leaderboard row and the choreography lab's candidate feed still resolve. In the choreography lab the "candidate" feed and the "today" feed are now the same for these signals.

## 5. Pitfalls & Lessons Learned

* A governance test used `kick` as its example of "a slot nothing produces"; a promotion breaks any test built on "this one is empty". Such tests should pick the slot from the list of empty ones.
* The first attempt to update the signal list rewrote the whole JSON file in another layout; it was reverted and edited as text.
* The listener's clock is the wall clock: a test that wants "audio has reached the speakers" must use a look-ahead of 0 or the offline clock, not a number of ticks.

## 6. Open Items & Next Steps

* [ ] Owner: see the kick and the bands drive a light before rating them (the proposal's first request); the lab mode `Kick_bands_mode` has known faults (weak punch to the eye, too many flashes).
* [ ] Measure the cost on the Raspberry Pi.
* [ ] `kick_present` stays on too long (right 71% of the time while the kick is out); the kick is weakest on the electronic tracks, where the truth itself is less sure.
* [ ] `band_sub` stays empty: the front end has no band under 60 Hz.
* [ ] Write down the promotion steps in the research skills.
