# Live sound against audio files: what the installation's analyzer really gets (2026-11-27)

Measured by `research/scoreboard/live_path.py`, which replays each road offline on the 20 truth tracks and
grades beats and tempo exactly as the scoreboard does. Production analyzer (`DyadicMetricalAudioAnalyzer`),
5 s look-ahead. The replay is perfectly regular; the real sound card, task and loop are not.

## Result

| Road | Beats | Tempo | One-frame beat flags a 30 fps display sees | Beats as the display sees them |
|---|---|---|---|---|
| Audio file (MP3), and every lab tool | 77 | 67 | 48% | 51 |
| **Spotify or aux, as the code was until 2026-11-27** | **22** | **58** | 100% | **22** |
| Spotify or aux, through the real connector after fix A only | 80 | 67 | 50% | 55 |
| **Spotify or aux, the installation as it is now (fix A and fix B)** | **80** | **67** | **100%** | **79** |
| Spotify or aux, if the display loop ran at 60 | 79 | 68 | 100% | 79 |
| Proposed: analyzer ticked by the audio | 78 | 67 | 49% | 52 |
| Proposed, and flags held until read | 78 | 67 | 100% | 78 |

Scores from 0 to 100, averaged over 20 tracks. The first line reproduces the scoreboard (77 and 67), which
checks the replay itself.

## Finding 1: on Spotify and aux, the beats are in the wrong place

- With an audio file, the file player advances the analyzer itself, exactly 60 times per second of music
  (`connectors/Local_AudioFile.py`, `advance_ingest_frame`).
- With live sound, nothing does that. `connectors/Local_Microphone.py` only refreshes the spectrum; the
  analyzer is advanced by the display loop, `core/Mode_master.py`, once per loop, and the loop runs at
  `target_fps`, 30 in `config/app_config.json`.
- The analyzer counts time in sixtieths of a second (`odf_fps = 60.0` in `music/MultiBandOnsetAudioAnalyzer.py`):
  its memory of the last seconds, its tempo templates and the place where it puts each beat all assume 60.
- At 30 it still finds the tempo most of the time, and about the right number of beats, but not where they fall:
  22 against 77. Every one of the 20 tracks drops (Another One Bites The Dust 96 to 5, Palladium 99 to 11).

## Finding 2: half of the one-frame signals never reach the lights

A beat is announced by a flag that is true for one analyzer tick (a sixtieth of a second) and cleared on the
next. The display loop looks 30 times a second. When the analyzer runs at 60, a flag raised and cleared between
two looks is never seen: 48% are seen. This concerns audio files today, and would concern live sound once
finding 1 is fixed. It only matters for modes that wait for the flag (`is_beat`, `is_real_beat`, `drop_hit`);
modes that follow the continuous beat position are not affected.

The choreography lab does not have this problem (it draws on every tick), so it currently flatters such modes.

## The fix

**Fix A was applied on 2026-11-27, with the owner's approval** (`connectors/Local_Microphone.py`, `step_analyzer`; tests in `tests/test_local_microphone_clock.py`). The table's third line is the real connector code replayed on the 20 tracks.

**Fix B was applied the same day, with the owner's approval** (`music/MusicSignals.py` `DisplayHold`, `music/Listener.py` `begin_display_frame`, `music/MusicalContextEngine.py`, `core/Mode_master.py`; tests in `tests/test_listener_display_hold.py` and `tests/test_mode_master_display_frame.py`). The display loop now collects the one-frame signals once per frame: all are seen, and the beats as the display sees them score 79. The same mechanism serves audio files, since it sits in the `Listener` and the display loop, not in a connector; that road was not replayed again through the real file player.

**A. Tick the analyzer by the audio, for live sound too.** In `connectors/Local_Microphone.py`, for every 735
new samples received, compute the spectrum of the window ending there and call `listener.update(fixed_dt=1/60)`,
as the file player does; mark the listener as externally clocked so the display loop stops ticking it. About
25 lines in one connector. Measured: 78 on beats, the same as audio files.

**B. Hold one-frame signals until the display has read them.** The `Listener` keeps "happened since the last
display frame" for each one-frame signal, and the display loop collects them once per frame. This touches the
sealed `music/` sector and `core/Mode_master.py`. Measured: 100% of the flags seen, 78 as the display sees them.

**Alternative, zero code:** set `target_fps` to 60. It fixes both in the replay (79), but doubles the drawing
work and the data sent to the LEDs, and only holds if the loop really keeps 60; when it does not, the analyzer
is again at the wrong speed. A is robust to a slow loop; this is not.

## What is not verified

- **Update, 2026-11-27:** after fixes A and B the owner tried the installation and reported that everything looks
  good. That is a judgement by eye and ear, with no detail on inputs and modes; the points below stay unmeasured.
- Nothing was measured on the real installation, before or after the fix. The owner can check by ear: with
  Spotify or aux, the lights should now be as much on the beat as with an MP3 of the same song.
- The fix was exercised offline only. The real sound card, its latency reports and the task's real pace were not.
- The replay has no jitter. A real loop that drifts between 25 and 35 frames per second makes the live road
  worse than measured here, not better.
- The share of modes that depend on one-frame flags was not counted.
