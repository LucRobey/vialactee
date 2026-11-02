# [2026-11-02] Test Suite Cleanup, 16-Band Mel Alignment & Headless Speedup

> **Date:** 2026-11-02  
> **Session ID:** `c7ae9eaf-2ce7-4142-94d0-6f712767d2f6`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Execute the 4-priority test-suite cleanup: replace the vacuous spectral delay test in `test_listener.py`, align remaining 8-band mocks/diagnostics to the 16-band Mel spectrum, mock `sounddevice.OutputStream` & cache `Genesis.mp3` in `test_structural_annotator.py`, and deduplicate/clean up stale tests.  
> **Status:** COMPLETED  
> **Commits:** `20a0044` (pushed: yes)  
> **Skills Used:** `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* Following the codebase-wide upgrade from 8 to 16 visual Mel FFT bands (`576cafc`) and recent mode/choreography reworks (`Extending_waves_mode`, `Shining_stars_mode`, `Opposite_sides_mode`), an audit of the `tests/` suite identified four categories of issues:
  1. **Priority 1 (Vacuous Delay Test):** `TestListener.test_spectral_delay_queue_synchronization` in [`tests/test_listener.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_listener.py) manually popped `self.listener._spectral_delay_queue` in an inline `while` loop and assigned `_delayed_*` fields in test code instead of calling `Listener.update()`, testing a copy of the queue logic rather than the production implementation.
  2. **Priority 2 (16-Band Mismatches & Stale Mode Mocks):**
     * [`tests/test_all_modes_musical_context.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_all_modes_musical_context.py) stimulated `Extending_waves_mode` using only `sound_power` (missing 16-band `asserved_fft_band`/`band_flux` and `_enter_progress = 1.0`) and fed 8-element `band_proportion` arrays to `Proportion_rainbow_mode` (whose guard `len(props) >= nb_bands` with `nb_bands = 16` caused it to fall back to uniform buckets).
     * [`tests/governance/test_mode_choreography.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_mode_choreography.py) still ran `test_all_registered_modes_16_bands_diagnostic` as an alternate-band check even though `DEFAULT_NB_BANDS` and `CALIBRATED_FOR["nb_bands"]` are now `16`, leaving `nb_bands=8` untested.
     * [`tests/test_mode_render.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_mode_render.py) and [`tests/test_opposite_sides_mode.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_opposite_sides_mode.py) had 8-element band arrays or missing `mock_listener.context = None` on `Shining_stars_mode` mocks.
     * [`tests/test_analyzer_contract_compliance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_analyzer_contract_compliance.py) still named its Mel flux test `test_band_flux_is_8_band_mel_flux` and only checked up to band index `7`.
  3. **Priority 3 (Slow Hardware/Disk I/O in Structural Annotator Tests):** [`tests/test_structural_annotator.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_structural_annotator.py) opened real `sounddevice.OutputStream` PortAudio streams during `AudioStreamer` tests and decoded `Genesis.mp3` from disk 7 times in `TestStructuralAnnotatorAppHeadless`.
  4. **Priority 4 (Merges, Deduplication & Stale Naming):**
     * [`tests/test_base_analyzer_contract.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_base_analyzer_contract.py) overlapped with [`tests/test_analyzer_contract_compliance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_analyzer_contract_compliance.py).
     * [`tests/test_udp_sender_throttling.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_udp_sender_throttling.py) duplicated the 10 Hz `analyzer_state` sideband throttle test from [`tests/governance/test_axiom_04_network_limits.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_axiom_04_network_limits.py) and had a stale `CustomBaseAnalyzer.update(self)` signature.
     * Stale docstrings and test names remained in [`tests/governance/test_mode_choreography_profiles.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_mode_choreography_profiles.py), [`tests/test_musical_context_engine.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_musical_context_engine.py), and [`tests/test_app_config_store.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_app_config_store.py).

---

## 2. Changes Made

### Priority 1 — Real `Listener.update()` Delay Queue Synchronization Test
* **[MODIFY]** [`tests/test_listener.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_listener.py):
  * Rewrote `TestListener.test_spectral_delay_queue_synchronization` to patch `music.Listener.time.time` and drive `self.listener.update(fixed_dt=dt)` across three timestamps (`t0 = 1000.0`, `t0 + 2.0`, `t0 + 5.1`) with 5.0s speaker delay (`time_delay = 5000`), verifying that 16-band spectral payloads, `beat_tag`, `rhythm_salience`, `beat_trust`, and sticky `novelty_detector` flags (`is_song_change`, `is_verse_chorus_change`, `asserved_novelty`, `combined_novelty`) remain held before 5.0s and flush accurately at `t0 + 5.1s`.

### Priority 2 — 16-Band Mel Alignment & Mode Test Stimulus Repair
* **[MODIFY]** [`tests/test_all_modes_musical_context.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_all_modes_musical_context.py):
  * Updated `test_metronome_and_wave_modes_behavioral_requirements` so `Extending_waves_mode` receives `_enter_progress = 1.0` and 16-band `asserved_fft_band` / `band_flux` arrays in both silence and energetic phases, testing real wavelength-stream rendering and confirming lower output during silence (`energy=0.05`, `sound_power=0.05`) than during energetic bass/transient excitation (`energy=0.95`, `sound_power=0.95`).
  * Updated `test_bar_modes_and_physics_behavioral_requirements` and `test_proportion_rainbow_and_beat_tag_consumption` from 8-element to 16-element arrays so `Proportion_rainbow_mode` satisfies `len(props) >= nb_bands` (`16`) and renders genuine skewed vs uniform band proportions.
* **[MODIFY]** [`tests/governance/test_mode_choreography.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_mode_choreography.py):
  * Replaced `test_all_registered_modes_16_bands_diagnostic` with `test_all_registered_modes_8_bands_diagnostic` (`nb_bands=8`) so legacy 8-band compatibility is tested alongside the primary 16-band (`DEFAULT_NB_BANDS`) calibration matrix, and updated docstrings/comments to reference `DEFAULT_NB_BANDS` (`16`).
* **[MODIFY]** [`tests/test_mode_render.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_mode_render.py):
  * Repaired `Shining_stars_mode` unit tests (`test_shining_stars_spawns_on_peak`, `test_shining_stars_colors_from_palette`, `test_shining_stars_fades_to_black`) by explicitly setting `self.mock_listener.context = None` and providing 16-element `band_flux` / `asserved_fft_band` arrays.
* **[MODIFY]** [`tests/test_opposite_sides_mode.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_opposite_sides_mode.py):
  * Expanded all 8-element `asserved_fft_band` and `band_flux` mock arrays to 16 elements matching `nb_of_fft_band = 16`.
* **[MODIFY]** [`tests/test_analyzer_contract_compliance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_analyzer_contract_compliance.py):
  * Renamed `test_band_flux_is_8_band_mel_flux` to `test_band_flux_is_16_band_mel_flux`, updated docstrings/comments to reflect the 16-band Mel filterbank, and added verification for band index `15` (`~14080 Hz` sine wave).

### Priority 3 — Headless Audio & Single Track Decode in `test_structural_annotator.py`
* **[MODIFY]** [`tests/test_structural_annotator.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_structural_annotator.py):
  * Mocked `tools.structural_annotator.sd.OutputStream` in `TestAudioStreamer.setUp` so `AudioStreamer.play()` / `pause()` tests never open real OS PortAudio streams.
  * Added `TestStructuralAnnotatorAppHeadless.setUpClass` to decode `Genesis` once and patch `resolve_audio_file` / `_load_audio_fallback` across the 7 headless app tests (cutting `test_structural_annotator.py` runtime from ~8s to ~0.9s while preserving real `resolve_audio_file` testing in `test_arbitrary_track_path_resolution`).

### Priority 4 — Test Consolidation, Deduplication & Naming Cleanup
* **[MODIFY / DELETE]** [`tests/test_analyzer_contract_compliance.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_analyzer_contract_compliance.py), [`tests/test_base_analyzer_contract.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_base_analyzer_contract.py), [`docs/contracts/music_analyzer_contract.md`](file:///c:/Users/lucro/Desktop/vialactee/docs/contracts/music_analyzer_contract.md):
  * Folded `DummyMinimalAnalyzer`, `test_minimal_subclass_defaults`, and `ANALYZER_REGISTRY` checks into `TestAnalyzerContractCompliance`, deleted `tests/test_base_analyzer_contract.py`, and updated the contract test path reference in `docs/contracts/music_analyzer_contract.md`.
* **[MODIFY]** [`tests/governance/test_axiom_04_network_limits.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_axiom_04_network_limits.py), [`tests/test_udp_sender_throttling.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_udp_sender_throttling.py):
  * Consolidated the 10 Hz `analyzer_state` sideband throttle assertions (including payload key verification) into `test_axiom_04_network_limits.py`, removed the duplicate method from `test_udp_sender_throttling.py`, closed the real UDP socket in `TestUdpSenderThrottling.setUp`, and updated `CustomBaseAnalyzer.update(self, fft_values, power, dt=0.016)` to match `BaseAudioAnalyzer.update`.
* **[MODIFY]** [`tests/governance/test_mode_choreography_profiles.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/governance/test_mode_choreography_profiles.py), [`tests/test_musical_context_engine.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_musical_context_engine.py), [`tests/test_app_config_store.py`](file:///c:/Users/lucro/Desktop/vialactee/tests/test_app_config_store.py):
  * Updated stale docstrings (`8 modes` $\to$ `13 modes`, retired `Beat_runner`/`Rhythm_breather` $\to$ `Power_bar_mode`/`Middle_bar_mode`), removed the duplicate 16-band assertion block in `test_spectral_tilt_and_vertical_center`, and renamed `test_preset_repository_init` $\to$ `test_app_config_store_init`.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/test_listener.py tests/test_structural_annotator.py -v`
  * **Result**: `25 passed in 1.05s`
* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `555 passed, 5 deselected, 100 subtests passed in 31.44s`

---

## 4. Architecture Decisions & Trade-offs

* **Decision 1 (Testing `Listener.update()` via mocked `music.Listener.time.time`)**: Rather than exposing internal queue helpers or duplicating pop loops in tests, patching `music.Listener.time.time` and feeding `update(fixed_dt=dt)` exercises the exact `_spectral_delay_queue` enqueue/dequeue path, sticky novelty accumulators, and `MusicalContextEngine.update()` integration.
* **Decision 2 (Keeping `test_casting_and_memory.py` at 5,000 iterations)**: Preserved the 5,000-frame zero-allocation soak test (`~0.16s` runtime) intact while reclaiming ~7 seconds of wall-clock time by eliminating redundant MP3 decoding and PortAudio stream initialization in `test_structural_annotator.py`.

---

## 5. Pitfalls & Lessons Learned

* **`DyadicMetricalAudioAnalyzer` read-only novelty properties**: `asserved_novelty`, `combined_novelty`, `is_song_change`, and `is_verse_chorus_change` on `DyadicMetricalAudioAnalyzer` delegate via `@property` to `self.novelty_detector` without setters; tests injecting synthetic novelty events on a real analyzer instance should mutate `listener.analyzer.novelty_detector`.
* **Contract doc path parity**: Deleting or merging a test file referenced in `docs/contracts/*.md` triggers `tests/governance/test_docs_parity.py` (`test_all_markdown_links_and_backtick_paths_resolve`) unless the markdown reference is updated in lockstep.

---

## 6. Open Items & Next Steps

* [ ] Monitor 16-band choreography dominance margins across real audio tracks as new modes or shader tweaks are introduced.
