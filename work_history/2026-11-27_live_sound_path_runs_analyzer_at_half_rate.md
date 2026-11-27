# 2026-11-27 On Live Sound the Analyzer Runs at Half Its Rate

> **Date:** 2026-11-27  
> **Session ID:** `71d81268-3807-434b-a0b6-70555148b388`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Check whether the analyzer behaves on live sound (Spotify, aux) as it does on audio files, after noticing that the display loop runs at 30 and every lab tool steps the analyzer at 60.  
> **Status:** COMPLETED (fault measured offline on 20 tracks; fixes A and B applied with the owner's approval and measured offline; not verified on the installation)  
> **Commits:** `97676ee` (fix A), `4d6f024` (replay) (pushed: no)  
> **Skills Used:** none  
> **Skill Friction:** `vialactee-dsp-engine`: states that the analyzer ticks at 60 Hz without saying who ticks it; nothing warns that the live connector leaves this to a 30 FPS loop.

---

## 1. Context & Motivation

* While fixing the choreography lab's timing, the display loop's pacing was read: `core/Mode_master.py` runs at `target_fps` (30) and calls `listener.update()` once per loop unless the listener is "externally clocked". Only the audio-file connector sets that flag. The owner uses Spotify, aux and MP3 files.

---

## 2. Changes Made

* **[NEW]** [`research/scoreboard/live_path.py`](../research/scoreboard/live_path.py): offline replay of five roads on a made-up clock (audio file; live sound as written; live sound with the loop at 60; analyzer ticked by the audio; the same with one-frame flags held), graded with the scoreboard's functions.
* **[NEW]** [`research/scoreboard/runs/live_path/LIVE_PATH.md`](../research/scoreboard/runs/live_path/LIVE_PATH.md) and `scores.json`: result, the two findings, the proposed fix.
* **[NEW]** [`research/tests/test_live_path.py`](../research/tests/test_live_path.py): 5 tests on a made-up song. Two of them document the fault and are expected to change when it is fixed.

### Fix A, applied after the owner's approval
* **[MODIFY]** [`connectors/Local_Microphone.py`](../connectors/Local_Microphone.py): the audio ring is four windows long and counts the samples received; `step_analyzer` makes one analyzer tick (`process_raw_audio` on the window ending there, `listener.update(fixed_dt=1/60)`) per 735 samples received, at most 6 per call, skipping ahead when more than 12 behind; `dynamic_audio_latency` now includes the audio received after the window; `listener.is_externally_clocked` is set while the stream runs and cleared when it stops or fails, so `core/Mode_master.py` ticks the listener only when no audio device does.
* **[NEW]** [`tests/test_local_microphone_clock.py`](../tests/test_local_microphone_clock.py): 6 tests (one tick per 735 samples with the right window, ticks follow the audio and not the number of calls, catch-up and skip, latency, and the real connector with a real `Listener` finding the beats of a made-up song).
* **[MODIFY]** [`docs/architecture/audio_pipeline.md`](../docs/architecture/audio_pipeline.md) (section 1.1, who advances the analyzer) and the `vialactee-dsp-engine` skill (one rule).
* **[MODIFY]** `research/scoreboard/live_path.py`: a `connector` road that drives the real `Local_Microphone` class.

### Fix B, applied after the owner's approval
* **[MODIFY]** [`music/MusicSignals.py`](../music/MusicSignals.py): `EVENTS`, `FLAGS` and `DisplayHold`, which remembers after each tick the one-frame signals that fired and publishes them once per display frame.
* **[MODIFY]** [`music/Listener.py`](../music/Listener.py): `begin_display_frame()`; `_tick(name)` (the value on the current tick) and `_flag(name)` (held value once the display runs); the seven one-frame properties and `signals` go through them; `_bridge_signals` reads tick values. 433 to 465 lines.
* **[MODIFY]** [`music/MusicalContextEngine.py`](../music/MusicalContextEngine.py): its per-tick logic reads the tick value (`_now`); `is_real_beat` and `is_drop_impact` are held the same way.
* **[MODIFY]** [`core/Mode_master.py`](../core/Mode_master.py): calls `listener.begin_display_frame()` once per frame, after the listener block and before the modes draw.
* **[MODIFY]** [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md): section 1.1, door 3 and the attribute table.
* **[NEW]** [`tests/test_listener_display_hold.py`](../tests/test_listener_display_hold.py) (9 tests) and [`tests/test_mode_master_display_frame.py`](../tests/test_mode_master_display_frame.py) (2 tests).

Until the display loop calls `begin_display_frame()` once, every property shows the tick value: benchmarks, studios and tests that read after each tick are unchanged.

---

## 3. Verification & Testing

* **Command**: `python -m pytest -q`
  * **Result**: 718 passed, 5 deselected, 409 subtests passed (701 before fix A, 707 before fix B).
* **Replay, 20 tracks, production analyzer** (0 to 100):

| Road | Beats | Tempo | One-frame flags seen at 30 fps | Beats as the display sees them |
| :--- | ---: | ---: | ---: | ---: |
| Audio file, and every lab tool | 77 | 67 | 48% | 51 |
| Spotify or aux, as written | 22 | 58 | 100% | 22 |
| Spotify or aux, loop at 60 | 79 | 68 | 100% | 79 |
| Spotify or aux through the real connector after fix A | 80 | 67 | 50% | 55 |
| **The same with the display loop collecting (fix B): the installation now** | **80** | **67** | **100%** | **79** |
| Analyzer ticked by the audio (replay of the idea) | 78 | 67 | 49% | 52 |
| The same, flags held until read | 78 | 67 | 100% | 78 |

  * The first line equals the scoreboard (77 and 67): the replay is consistent with it.
  * Every track drops on the live road; the largest falls are Another One Bites The Dust (96 to 5) and Palladium (99 to 11).

---

## 4. Architecture Decisions & Trade-offs

* **Replay, not a patch.** The fault sits in the installation's own code; reproducing the road offline measures it on the truth without touching production, and gives a number for each candidate fix.
* **Proposed fix A before the zero-code alternative.** Raising `target_fps` to 60 also restores the score in the replay, but it depends on the loop holding 60; ticking the analyzer by the audio does not.

---

## 5. Pitfalls & Lessons Learned

* **Every benchmark so far measured the audio-file road.** The old leaderboard, the scoreboard and the choreography lab all step at 60. None could have seen this.
* **A one-frame flag is a fragile interface between a 60-tick producer and a 30-frame reader.** About half are lost. The choreography lab draws on every tick, so it flatters modes that wait for such flags.
* **The replay is regular.** Real jitter can only make the live road worse than measured.

---

## 6. Open Items & Next Steps

* [ ] Owner: check both fixes by ear on the installation (Spotify or aux against an MP3 of the same song; modes that flash on the beat).
* [ ] Make the scoreboard and the choreography lab read signals the way the display does (30 frames a second, `begin_display_frame`); today they read every tick.
* [ ] A test caught that the bridged slots of `listener.signals` were built from held values and arrived one frame late; fixed, keep the test.
* [ ] Count the modes that depend on one-frame flags.
