# Session Log: Audit, Mode Choreography Reworks (C1–C6), and Transition Coherence Extensions (D1–D6)

**Date:** 2026-11-02  
**Author / Agent:** Antigravity  
**Status:** COMPLETED  
**Commits:** `66007de`, `23c37f0`, `975f5fa`, `fb1d06e`, `094e742`, `73a67f0`, `cd178fc`, `0c4b9d4`

---

## 1. Objective & Context

Execute the **Vialactée – Audit & Plan (2026-11-02)** end-to-end across Phases A, B, C, D, and E:
- **Phase A (Housekeeping):** Backfill missing session logs (`2edcb22`, `a7b4c62`, `87c143d`, `494b438`), tick the stale Law 7 open item in [`work_history/2026-10-29_environment_fixes.md`](2026-10-29_environment_fixes.md), fix broken `file:///c:/Users/Users/...` links in [`work_history/README.md`](README.md), and document `.venv` interpreter usage in [`docs/manuals/developer_tools.md`](../docs/manuals/developer_tools.md).
- **Phase B (Real-Audio Audit):** Optimize [`tools/choreography_probe.py`](../tools/choreography_probe.py) (`_run_modes_batch_on_audio`) so `measure_all_modes_on_audio` runs a single shared `Listener` + `Mood` DSP pass per track (~7.5x faster with identical deterministic metrics), and run the 4-track historical probe (`Another One Bites The Dust`, `Boogie Wonderland`, `Django`, `Feeling Good` in `assets/musics/mp3_files/`, `25s..70s`).
- **Phase C (Mode Improvements C1–C6):**
  - **C1 (`Chromatic_chaser_mode`):** Twin runners sweeping from both ends (`0` and `n - 1`) to collide at the center as `beat_phase` moves `0 -> 1`, with `ctx.energy` scaling the leading spark halo and collision burst (`d(beat)` >= 40% of audio budget; `R_std(-all)` well below 19).
  - **C2 (`Bary_rainbow_mode`):** Remove undeclared `ctx.energy` (`level`) from brightness/saturation and interpolate `asserved_fft_band` radially from center (bass) to outer tips (treble) so `d(spectrum) >= 2x` next driver.
  - **C3 (`Shining_stars_mode`):** Scale star count per sub-segment (`1..2` on strong `band_flux`), widen the soft 5-LED star halo, and boost peak core brightness (`R_std(full) > 8` on `groove_lock` without exceeding star-rate limits).
  - **C4 (`Extending_waves_mode`):** Decouple wave spawning from beat ticks (`is_tick`); spawn outward waves from a continuous level accumulator (`self.level_accum`) so `beat` only tints wave color and crest shimmer.
  - **C5 (`Middle_bar_mode`):** Blend the outer 2-LED bass caps toward pure white `self.white = (255, 255, 255)`.
  - **C6 (`Opposite_sides_mode`):** Add a 1-LED darkened contrast collar (`_collar` dimming ±1 wing neighbors by 55% around active pinpoints without touching the fixed core) and crisp depop threshold (`0.35` with `3.0x` slope) for the firework crackle (`IDEAS.md` #4).
- **Phase D (Transitions & Coherence D1–D6):**
  - **D1:** Audit transition durations and enforce `MIN_SHOWSTOPPER_DURATION = 1.5s` across all `ROOM_EPI_2D` and `ROOM_SWEEP_2D` showstoppers in `TRANSITION_TECHNIQUES` (`explosion` `1.8s`, `transient_blip` `1.8s`, `weird_glitch` `1.6s`, `global_change` `1.8s`, `directional_wipe` / `vertical_wipe` `1.5s`, `wipe_left_to_right` / `wipe_right_to_left` `1.6s`).
  - **D2 & D3:** Add `partialRerollProb` (`[0.0, 1.0]`, default `0.0`, `0.30` in `coherence_full.json`/`coherence_small.json`) and `max_reroll_groups` support to [`transitions/policy.py`](../transitions/policy.py), [`transitions/casting.py`](../transitions/casting.py), and [`transitions/manager.py`](../transitions/manager.py) so micro-transitions and partial re-rolls retarget only 1–2 groups while keeping remaining groups pinned to their active modes.
  - **D4:** Add `wildcardProb` (`[0.0, 1.0]`, default `0.0`, `0.08` in `coherence_full.json`/`coherence_small.json`) and `wildcard` flag to [`transitions/casting.py`](../transitions/casting.py) so soft rule weights are ignored with 5–10% probability while **never** relaxing hard `forbid` rules.
  - **D6:** Implement the bespoke cooperative exit transition pilot on [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py): during `on_transition_exit`, outward waves bleach to pure white `(255, 255, 255)` and stack/accumulate from the outer edges inward until the strip fills with white.
- **Phase E (Headless Live Validation):** Run a 60-second (3,600-frame) headless multi-mode and transition simulation verifying transition cadence, partial re-rolls, 0 forbid violations, and AXIOM-01 frame budget (`0.057 ms/mode/frame <= 0.20 ms`).

---

## 2. Synthetic & 4-Track Real-Audio Choreography Matrix Results (Post-Phase C)

### 2.1 Synthetic `groove_lock` Profile (`beat_trust=0.68, salience=0.55, rhythm_lock=0.50`)

| Mode | Lead | Sec | `R_std(full)` | `R_std(-lead)` | `R_std(-all)` | `d(lead)` | `d(sec)` | `R_diff` |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `Rainbow_mode` | `spectrum` | `none` | 30.76 | 4.50 | 3.71 | +26.26 | +0.00 | 3.25 |
| `Bary_rainbow_mode` | `spectrum` | `beat` | **33.34** | **1.65** | **0.52** | **+31.69** | +0.13 | 3.21 |
| `Middle_bar_mode` | `beat` | `spectrum` | **46.41** | 11.59 | 6.75 | **+34.82** | -2.32 | 7.51 |
| `Shining_stars_mode` | `transient` | `spectrum` | **15.34** | **0.00** | **0.00** | **+15.34** | -0.70 | 2.02 |
| `Proportion_rainbow_mode` | `spectrum` | `none` | 44.26 | 2.93 | 2.16 | +41.33 | +0.00 | 4.80 |
| `Opposite_sides_mode` | `spectrum` | `transient` | **48.03** | 24.75 | 2.09 | **+23.28** | +1.61 | 5.39 |
| `Hyper_strobe_mode` | `transient` | `none` | 41.73 | 0.00 | 0.00 | +41.73 | +0.00 | 11.87 |
| `Chromatic_chaser_mode` | `beat` | `level` | **41.61** | **6.84** | **0.00** | **+34.77** | -1.01 | 8.04 |
| `Metronome_mode` | `beat` | `none` | 26.67 | 10.54 | 7.42 | +16.12 | +0.00 | 4.45 |
| `Coloured_middle_wave_mode` | `spectrum` | `beat` | 30.93 | 8.92 | 0.00 | +22.01 | +1.34 | 2.93 |
| `Impact_shockwave_mode` | `beat` | `level` | 36.73 | 17.14 | 0.00 | +19.58 | +0.07 | 6.70 |
| `Power_bar_mode` | `level` | `beat` | 39.93 | 20.78 | 3.91 | +19.15 | +11.30 | 5.27 |
| `Extending_waves_mode` | `level` | `beat` | **46.25** | **0.00** | **0.00** | **+46.25** | **+0.42** | 8.87 |

### 2.2 4-Track Real-Audio Probe (`25s..70s`, Before vs. After Phase C)

| Track (`assets/musics/mp3_files/`) | Mode | Pre `d(lead)` | Post `d(lead)` | Pre `R_std(-all)` | Post `R_std(-all)` | Post `R_std(full)` |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Queen – Another One Bites The Dust** (`lock=0.533`) | `Chromatic_chaser_mode` | +4.23 | **+34.86** | 25.74 | **6.12** | 43.78 |
| | `Bary_rainbow_mode` | +1.55 | **+5.55** | 32.16 | 31.86 | 38.29 |
| | `Shining_stars_mode` | +24.81 | **+31.40** | 0.99 | 1.95 | 35.22 |
| | `Extending_waves_mode` | +8.49 | **+14.59** | 12.11 | 20.10 | 34.66 |
| **Earth, Wind & Fire – Boogie Wonderland** (`lock=0.588`) | `Chromatic_chaser_mode` | +3.75 | **+32.62** | 17.55 | **1.55** | 36.75 |
| | `Bary_rainbow_mode` | +1.98 | **+20.84** | 17.07 | **4.87** | 26.65 |
| | `Shining_stars_mode` | +27.32 | **+36.66** | 0.98 | 1.97 | 38.63 |
| | `Extending_waves_mode` | +11.12 | **+20.37** | 8.31 | 12.04 | 32.38 |
| **Django Reinhardt – Django** (`lock=0.218`) | `Chromatic_chaser_mode` | +3.63 | **+35.41** | 31.34 | **5.57** | 43.75 |
| | `Bary_rainbow_mode` | +2.90 | **+23.70** | 33.89 | **5.14** | 29.81 |
| | `Shining_stars_mode` | +19.51 | **+26.20** | 0.85 | 1.35 | 44.77 |
| | `Extending_waves_mode` | +12.56 | **+21.43** | 15.65 | 13.53 | 36.92 |
| **Michael Bublé – Feeling Good** (`lock=0.268`) | `Chromatic_chaser_mode` | +5.14 | **+38.43** | 31.22 | **5.23** | 46.22 |
| | `Bary_rainbow_mode` | +3.39 | **+22.96** | 31.94 | **6.03** | 29.78 |
| | `Shining_stars_mode` | +19.83 | **+26.88** | 0.99 | 1.68 | 45.38 |
| | `Extending_waves_mode` | +10.22 | **+15.21** | 22.84 | 21.40 | 38.19 |

---

## 3. Files Modified

- **Modes & Probes (Phases B & C):**
  - [`modes/Chromatic_chaser_mode.py`](../modes/Chromatic_chaser_mode.py)
  - [`modes/Bary_rainbow_mode.py`](../modes/Bary_rainbow_mode.py)
  - [`modes/Shining_stars_mode.py`](../modes/Shining_stars_mode.py)
  - [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py)
  - [`modes/Middle_bar_mode.py`](../modes/Middle_bar_mode.py)
  - [`modes/Opposite_sides_mode.py`](../modes/Opposite_sides_mode.py)
  - [`tools/choreography_probe.py`](../tools/choreography_probe.py)
- **Transitions & Coherence (Phase D):**
  - [`transitions/policy.py`](../transitions/policy.py)
  - [`transitions/casting.py`](../transitions/casting.py)
  - [`transitions/manager.py`](../transitions/manager.py)
  - [`transitions/service.py`](../transitions/service.py)
  - [`config/coherence.schema.json`](../config/coherence.schema.json)
  - [`config/coherence_loader.py`](../config/coherence_loader.py)
  - [`config/coherence_full.json`](../config/coherence_full.json)
  - [`config/coherence_small.json`](../config/coherence_small.json)
  - [`tools/coherence_helper.html`](../tools/coherence_helper.html)
- **Tests & Docs (Phases A, C, D):**
  - [`tests/test_mode_helpers.py`](../tests/test_mode_helpers.py)
  - [`tests/test_extending_waves.py`](../tests/test_extending_waves.py)
  - [`tests/test_all_modes_musical_context.py`](../tests/test_all_modes_musical_context.py)
  - [`tests/test_opposite_sides_mode.py`](../tests/test_opposite_sides_mode.py)
  - [`tests/test_coherence_loader.py`](../tests/test_coherence_loader.py)
  - [`tests/transitions/test_families_and_handshake.py`](../tests/transitions/test_families_and_handshake.py)
  - [`tests/transitions/test_casting_and_memory.py`](../tests/transitions/test_casting_and_memory.py)
  - [`tests/transitions/test_manager.py`](../tests/transitions/test_manager.py)
  - [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md)
  - [`docs/reference/configuration_schemas.md`](../docs/reference/configuration_schemas.md)
  - [`docs/contracts/transition_contract.md`](../docs/contracts/transition_contract.md)
  - [`docs/manuals/developer_tools.md`](../docs/manuals/developer_tools.md)
  - [`docs/ideas/IDEAS.md`](../docs/ideas/IDEAS.md)

---

## 4. Verification & Test Outcomes

- **Post-Review Hardening Fixes:**
  - Synced [`tools/coherence_helper.html`](../tools/coherence_helper.html) (`DEFAULT_SETTINGS`, `validate`, `sampleOnce`, and `Settings` sidebar panel) with `partialRerollProb` and `wildcardProb`, and added parity test `test_coherence_helper_html_default_settings_match_schema_and_configs` in [`tests/test_coherence_loader.py`](../tests/test_coherence_loader.py).
  - Hardened partial re-roll in [`transitions/casting.py`](../transitions/casting.py), [`transitions/manager.py`](../transitions/manager.py), and [`transitions/service.py`](../transitions/service.py) so kept groups are guaranteed to be in unison (`all(active_by_id.get(s, "") == cur_m for s in fg.free_segments)`), `wholeInstallation` is excluded when `want_partial=True`, partial re-rolls default to `smooth_cosine_crossfade`, and full-chandelier triggers (`request_drop`, `drop_impact`, `pre_drop_buildup`, `song_change`) always pass `allow_partial=False`.
  - Fixed high-speed (`speed >= 2.0`) collision burst wrap guard in [`modes/Chromatic_chaser_mode.py`](../modes/Chromatic_chaser_mode.py) (`wrapped` only triggers on actual phase wrap).
  - Coupled outgoing white waves in [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py) so arriving crests deposit inward onto `self._stack_frontier` during `on_transition_exit`.
- **Phase E Headless 60-Second Simulation (`TransitionService` + 13 Modes):**
  - `Boot allocation: 11 segments`
  - `60s sim complete: transitions=9, partial_rerolls=3, forbid_violations=0, mean_mode_ms=0.0570 ms/frame (AXIOM-01 cap <= 0.20 ms)`
- **Full Test Suite:**
  - `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` -> `555 passed, 5 deselected, 99 subtests passed in 33.29s`

---

## 5. Open Items & Next Steps

- [ ] Optional visual check in `python -m tools.mode_studio` with live playback to fine-tune any subjective aesthetics on physical hardware.
- [ ] Optional future extension in `transitions/policy.py`: adjacency rules between touching segment groups (`IDEAS.md` #2).
