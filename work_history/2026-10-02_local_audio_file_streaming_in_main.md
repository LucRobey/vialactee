# [2026-10-02] Local Audio File Streaming in Main.py

> **Date:** 2026-10-02  
> **Session ID:** `1f7b5ed5-125e-471d-973c-227ff917de25`  
> **Agent / Model:** Gemini 3.8 Flash (High)  
> **Primary Goal:** Enable `Main.py` to stream and analyze local MP3/WAV files with 5.0-second lookahead anticipation, 60 FPS sample-accurate DSP hardware parity with `tools/mode_studio.py` and `tools/music_studio.py`, simulator transport controls, and CLI argument parsing.  
> **Status:** COMPLETED

---

## 1. Context & Motivation

* Human developer requested the capability to run `Main.py` directly on local MP3 files with the same flexibility, lookahead parity, and transport experience available in the developer studios (`tools/mode_studio.py` and `tools/music_studio.py`).
* Previously, `Main.py` only accepted analog microphone capture via `connectors/Local_Microphone.py`, requiring external virtual audio cables or live microphone feeds to test chandelier modes in full system orchestration.

---

## 2. Changes Made

### Audio Ingestion & Connectors
* **[NEW]** [`connectors/Local_AudioFile.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Local_AudioFile.py):
  * Implemented `Local_AudioFile` (aliased as `AudioFile_Player`).
  * Features path resolution supporting absolute paths, cwd-relative paths, repo-relative paths, `assets/musics/mp3_files/`, omitted `.mp3` extensions, and case-insensitive fuzzy name matches.
  * Audio decoding and resampling using `soundfile` with automatic polyphase resampling to 44,100 Hz.
  * Generates separate stereo stream for physical soundcard playback via `sounddevice.OutputStream` and mono stream for FFT/ODF DSP analysis.
  * Measures PortAudio hardware DAC buffer latency (`dac_latency`).
  * Implements 5.0-second lookahead pre-roll (`prime_analyzer`) and sample-accurate 60 FPS frame stepping (`advance_ingest_frame`) in exact 735-sample increments.
  * Sets `listener.is_externally_clocked = True` and zeroes out artificial ADC microphone latency (`listener.dynamic_audio_latency = 0.0`).
  * Full transport controls: `toggle_pause()`, `seek()`, `seek_relative()`, `next_song()`, `prev_song()`, `change_song_number()`.
  * Asynchronous `play_forever()` and `listen_forever()` runners with auto-loop or playlist advancement upon track completion.

### Core Orchestration
* **[MODIFY]** [`core/Mode_master.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Mode_master.py):
  * Added guard `if not getattr(self.listener, "is_externally_clocked", False):` before `self.listener.update()` in `update()`.
  * Prevents double-stepping the `Listener` 5-second ring buffer when `Local_AudioFile` steps the DSP engine at 60 Hz in lockstep with the soundcard.

### Hardware & Simulator Interactivity
* **[MODIFY]** [`hardware/Fake_leds.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/hardware/Fake_leds.py):
  * Added `set_audio_player(audio_player)` to `FakeLedsVisualizer` and `Fake_leds`.
  * Wired Pygame keyboard shortcuts when an audio player is active:
    * `[Space]`: Toggle pause / play.
    * `[→] / [←]`: Seek forward / backward by 5 seconds.
    * `[N] / [P]`: Advance to next or return to previous track in playlist.
    * `[1] - [9]`: Jump directly to track 1 through 9.
  * Added live window caption telemetry showing track title, play/pause status, current time, total duration, and shortcut hints.

### Application Entrypoint & CLI Parsing
* **[MODIFY]** [`Main.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/Main.py):
  * Implemented `parse_arguments()` with CLI flags:
    * `--song`, `-s` / `song_pos`: Path or track name of MP3/WAV file (defaults to `Palladium.mp3` or first track if flag passed without value).
    * `--mic`, `--microphone`: Force physical microphone input.
    * `--loop`: Loop active track indefinitely.
    * `--mode`, `-m`: Set initial lighting mode across all segments via `seg.force_mode()`.
    * `--profile`, `-p`: Hardware profile override (`full` or `small`).
    * `--model`: Rhythm analyzer model class (`MultiBandOnsetAudioAnalyzer` or `AudioAnalyzer`).
    * `--server`: Enable web connector server.
    * `--panel`: Enable real-time music analyzer HUD overlay in the simulator.
    * `--config`, `-c`: Path to custom app configuration file.
  * Dynamic audio connector selection: chooses `Local_AudioFile` when song specified via CLI or config, otherwise defaulting to `Local_Microphone`.
  * Added high-precision 1ms timer period on Windows (`timeBeginPeriod(1)` / `timeEndPeriod(1)`).

### Documentation & Schemas
* **[MODIFY]** [`docs/reference/configuration_schemas.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/configuration_schemas.md):
  * Documented `song`, `audio_file`, and `loop` in the master configuration reference table.

### Unit Tests
* **[NEW]** [`tests/test_local_audio_file.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/test_local_audio_file.py):
  * 7 unit tests verifying audio loading, resampling, path resolution, lookahead priming, frame stepping, transport controls, CLI parsing, and simulator delegation.

---

## 3. Verification & Testing

* **Unit Tests**: `python -m pytest tests/test_local_audio_file.py`
  * **Result**: `7 passed in 6.86s`
* **Full Test Suite**: `python -m pytest`
  * **Result**: `193 passed, 5 deselected in 14.91s` (0 failures, 100% pass rate).
* **CLI Help Test**: `python Main.py --help`
  * **Result**: Exited with code 0; clean argument documentation printed.
* **Song Loading & Resolution Verification**:
  * Tested resolving and loading `Nightcall.mp3`: 258.4s duration loaded, `is_externally_clocked=True`.
* **Constitution Code Governance**:
  * Verified all production files adhere to the 500-line cap:
    * `Main.py`: 352 lines (cap: 500)
    * `connectors/Local_AudioFile.py`: 426 lines (cap: 500)
    * `hardware/Fake_leds.py`: 482 lines (cap: 500)
    * `core/Mode_master.py`: 604 lines (ratchet limit: 613)

---

## 4. Architecture Decisions & Trade-offs

* **Externally Clocked Flag**: `Listener.update()` must run in strict 735-sample increments (60 Hz) for `MultiBandOnsetAudioAnalyzer` ODF rolling and comb filter synchronization. Rather than having `Mode_master` and `Local_AudioFile` both call `listener.update()`, setting `listener.is_externally_clocked = True` delegates timing to the audio file streamer while keeping `Mode_master` decoupled at any target frame rate (30 or 60 FPS).
* **Duck-Typing Parity with `Local_Microphone`**: `Local_AudioFile` provides both `play_forever()` and `listen_forever()` methods so `Main.py` task management remains completely uniform.

---

## 5. Open Items & Next Steps

* All requested functionality is complete, tested, and verified across simulator, CLI, and core engine.
