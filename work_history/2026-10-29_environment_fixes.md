# [2026-10-29] Environment Fixes, Shining Stars Musical Dynamics & Multi-Profile Choreography Suite (Phases S1–S6)

> **Date:** 2026-10-29  
> **Session ID:** `2d58e975-bea2-417f-8e09-f651f1e7a628`  
> **Agent / Model:** Gemini 4 Argon (High)  
> **Primary Goal:** Align Mode Studio with production `Main.py` 8-band visual FFT & coarse Mel flux (S1), declare dev/benchmark dependencies and guard default `pytest` collection (S2), add an offline real-audio choreography probe (S3), fix `Shining_stars_mode.py` dominant-band onset clarity and spectral brightness scaling (S4a), add realistic synthetic rhythm-lock profiles and Law 1/Law 7 governance tests (S4b), and synchronize all documentation and skills (S5–S6).  
> **Status:** COMPLETED  
> **Commits:** `c68fb03` `08ca520` `4708f63` `d06e53b` `dc47f44` `2297efa` (pushed: yes)  
> **Skills Used:** `vialactee-project`, `vialactee-mode-creator`  
> **Skill Friction:** `vialactee-mode-creator`: referenced hardcoded `"8-band spectrum"` instead of band-count-agnostic `nb_of_fft_band` / `int(b * 255 / max(1, num_bands - 1))` (updated in Phase S5).

---

## 1. Context & Motivation

1. **Mode Studio vs Production Mismatch (`S1`):** `tools/mode_studio.py` previously initialized `Listener` with `nb_of_fft_band = 16` without `"visual_flux_source": "coarse_mel"`, whereas production `Main.py` runs `nb_of_fft_band = 8` with coarse Mel `band_flux`. Modes tuned in Studio therefore saw half the per-band energy and a different flux distribution than on the chandelier.
2. **Test Environment & Benchmark Collection (`S2`):** Running plain `pytest -q` collected `tests/test_benchmark_engine.py` (`mir_eval`), and resampling `48 kHz` MP3s required `scipy`, neither of which was isolated in `requirements-dev.txt` or guarded in `tests/conftest.py`.
3. **Real-Audio Telemetry & `Shining_stars_mode` Saturation (`S3`, `S4a`):** Probing real songs (`Queen - Another One Bites the Dust.mp3`, `Earth, Wind & Fire - Boogie Wonderland.mp3`, `Django.mp3`, `Michael Bublé - Feeling Good.mp3`) revealed that real-audio `rhythm_lock` averages `0.21–0.51` (much lower than the synthetic `0.82`). In `Shining_stars_mode.py`, the `(1.0 - lock) * band_val * self.threshold * 2.8` fallback fired every frame on steady band volume whenever `lock < 0.65`, spawning `198–397 stars/sec` across multiple harmonic-bleed bands at constant brightness.
4. **Synthetic Lock Profiles & Law 1 / Law 7 Interaction (`S4b`):** A single `high_lock` (`0.82`) synthetic clip did not test `groove_lock` (`0.50`) or `loose_lock` (`0.25`) regimes, nor did it document the `LOCK_CONFOUNDED` (`|Δlock| > 0.10`) effect when muting `beat` lifts `beat_trust -> 1.0`.

---

## 2. Changes Made

### Phase S1 — Studio Production Parity (`c68fb03`)
* **[NEW]** [`tools/listener_config.py`](../tools/listener_config.py):
  * Centralizes `PRODUCTION_VISUAL_FFT_BANDS = 8`, `SUPPORTED_STUDIO_FFT_BANDS = (8, 16)`, and `build_listener_infos(nb_bands)` setting `"visual_flux_source": "coarse_mel"`.
* **[MODIFY]** [`tools/mode_studio.py`](../tools/mode_studio.py):
  * Defaults to `8` visual FFT bands (`--bands {8, 16}`), displays `[visual FFT {N} · analyzer 32]` in the header, and dynamically renders `8` or `16` spectrum + flux bars in Card 1.
* **[NEW]** [`tests/test_studio_visual_bands.py`](../tests/test_studio_visual_bands.py):
  * Verifies `build_listener_infos()` parity with `Main.py` across 8 and 16 bands.

### Phase S2 — Dev Dependencies & Pytest Collection Guard (`08ca520`)
* **[NEW]** [`requirements-dev.txt`](../requirements-dev.txt):
  * Declares `-r requirements.txt`, `scipy>=1.11.0`, and `mir_eval>=0.7`.
* **[MODIFY]** [`tests/conftest.py`](../tests/conftest.py):
  * Skips `@pytest.mark.benchmark` modules during default `pytest -q` runs when optional benchmark dependencies are absent.

### Phase S3 — Offline Real-Audio Choreography Probe (`4708f63`)
* **[NEW]** [`tools/choreography_probe.py`](../tools/choreography_probe.py) & **[NEW]** [`tests/test_choreography_probe.py`](../tests/test_choreography_probe.py):
  * Implements `OfflineClock`, `load_audio_mono` (with `scipy.signal.resample_poly` for non-44.1 kHz files), `capture_telemetry`, and `measure_all_modes_on_audio`.
* **[MODIFY]** [`tools/choreography_matrix.py`](../tools/choreography_matrix.py):
  * Adds `--track`, `--start` (`25.0s`), and `--duration` (`45.0s`) CLI flags.

### Phase S4a — `Shining_stars_mode.py` Musical Dynamics & Dominant-Band Clarity (`d06e53b`)
* **[MODIFY]** [`modes/Shining_stars_mode.py`](../modes/Shining_stars_mode.py):
  * Removed `(1.0 - lock) * band_val * self.threshold * 2.8` continuous volume trigger.
  * Kept the mood gradient mapping (`palette_lut[self._band_lut_idx[i]]`), scaled each band's star color intensity by its actual spectral energy (`band_gain = 0.25 + 0.75 * band_val`, `SECONDARY = ("spectrum",)`).
  * On onset frames (`max_flux > current_threshold`), triggers only the dominant band(s) leading the attack (`flux_val > current_threshold and flux_val >= 0.50 * max_flux`).
  * Added a minimal Law 1 fallback when completely unlocked and flux-silent (`max_flux <= current_threshold` and `rhythm_lock < 0.35`), twinkling at most 1 star every 10 frames (`6 Hz`) in `argmax(bands) > 0.35`.

### Phase S4b — Synthetic Lock Profiles & Law 1-Aware Conformance Tests (`dc47f44`)
* **[MODIFY]** [`tools/choreography_matrix.py`](../tools/choreography_matrix.py):
  * Bumped `SYNTHETIC_CLIP_VERSION = "2"`, added `SYNTHETIC_PROFILES` (`high_lock`, `groove_lock`, `loose_lock`), `--profile {high_lock,groove_lock,loose_lock,all}`, and `lock_confounded_drivers` (`|Δlock| > 0.10`).
* **[MODIFY]** [`tests/governance/test_mode_choreography.py`](../tests/governance/test_mode_choreography.py) & **[NEW]** [`tests/governance/test_mode_choreography_profiles.py`](../tests/governance/test_mode_choreography_profiles.py):
  * Updated `CALIBRATED_FOR` with `"clip_version": "2"` and `"profiles": ("high_lock", "groove_lock", "loose_lock")`.
  * Enforced all 3 Law 7 assertions across all 8 modes in `CONFORMING_MODES_PHASE_4A` on both `high_lock` and `groove_lock`.
  * Added `test_loose_lock_modes_stay_alive` verifying `R_std(full) > 1.0` and `R_std(full) >= 0.20 * R_std(high_lock)` across all 13 modes.

### Phase S5 & S6 — Documentation & Skill Sync
* **[MODIFY]** [`docs/manuals/developer_tools.md`](../docs/manuals/developer_tools.md), [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md), [`docs/contracts/mode_contract.md`](../docs/contracts/mode_contract.md), [`.agents/skills/vialactee-mode-creator/SKILL.md`](../.agents/skills/vialactee-mode-creator/SKILL.md):
  * Documented Studio `--bands`, `requirements-dev.txt`, the 3 synthetic profiles, beat-mute `Δlock` behavior, `--track` real-audio probe, updated `Shining_stars_mode` catalog entry, and replaced hardcoded `8-band` / `int(b * 255 / 7)` wording with band-count-agnostic formulas.

---

## 3. Telemetry & Empirical Measurement Tables

### 3.1 Real-Audio Telemetry (`25s..70s`, 8 Visual FFT Bands)

| Track | `lock_mean` | `lock_p10` | `lock_p50` | `lock_p90` | `flux_p50` | `flux_p99` | `frac_flux > 10` | Old Stars/s | New Stars/s |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Queen - Another One Bites the Dust.mp3` | `0.506` | `0.369` | `0.502` | `0.648` | `0.0` | `51.8` | `0.156` | `207 / s` | `~30 / s` |
| `Earth, Wind & Fire - Boogie Wonderland.mp3` | `0.514` | `0.335` | `0.533` | `0.665` | `0.0` | `39.1` | `0.149` | `198 / s` | `~30 / s` |
| `Django.mp3` | `0.264` | `0.000` | `0.203` | `0.562` | `0.0` | `56.0` | `0.209` | `346 / s` | `~42 / s` |
| `Michael Bublé - Feeling Good.mp3` | `0.214` | `0.000` | `0.145` | `0.525` | `0.0` | `52.5` | `0.123` | `397 / s` | `~35 / s` |

### 3.2 Synthetic Choreography Matrix (`high_lock`, `groove_lock`, `loose_lock` — 8 Bands)

- **`high_lock` (`rhythm_lock = 0.82`) & `groove_lock` (`rhythm_lock = 0.50`):**
  All 8 modes in `CONFORMING_MODES_PHASE_4A` (`Bary_rainbow_mode`, `Shining_stars_mode`, `Opposite_sides_mode`, `Hyper_strobe_mode`, `Metronome_mode`, `Coloured_middle_wave_mode`, `Impact_shockwave_mode`, `Power_bar_mode`) pass strict `LEAD` dominance, `d(lead) >= 0.30 * (R_std(full) - R_std(-all))`, and `R_std(-sec) >= 0.65 * R_std(full)`.
  Specifically for `Shining_stars_mode`: `R_std(full) = 4.40`, `R_std(-lead) = 0.00`, `R_std(-sec) = 5.18`, `d(transient) = +4.40`, `d(beat) = 0.00`, `d(level) = 0.00`, `d(spectrum) = -0.78`.
- **`loose_lock` (`rhythm_lock = 0.25`):**
  All 13 registered modes stay alive (`R_std(full)` in `[9.49, 59.32]`, well above `1.0` and `>= 0.20 * R_std(high_lock)`).

---

## 4. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`
  * **Result**: `471 passed, 5 deselected, 91 subtests passed` (0 failures).
* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/governance/ -q -p no:cacheprovider`
  * **Result**: All governance tests (including `test_axiom_07_code_governance.py`, `test_docs_parity.py`, `test_mode_choreography.py`, and `test_mode_choreography_profiles.py`) pass with 0 violations.
* **AXIOM-07 Line Cap**: All governed production `.py` files and new test/tool files are well below the 500-line cap (`Shining_stars_mode.py`: 218 lines, `tools/choreography_matrix.py`: 490 lines, `tests/governance/test_mode_choreography.py`: 445 lines, `tests/governance/test_mode_choreography_profiles.py`: 186 lines).

---

## 5. Architecture Decisions & Trade-offs

* **Dominant-Band Onset Gating (`>= 0.50 * max_flux`):** A percussive hit (kick or snare) produces harmonic bleed across adjacent Mel bands. Filtering onset triggers to bands with `flux_val >= 0.50 * max_flux` preserves single-color frequency readability on each attack while still allowing simultaneous kick + hi-hat hits of comparable strength to spawn both colors.
* **Brightness Scaling via `asserved_fft_band` (`0.25 + 0.75 * band_val`):** Gives `SECONDARY = ("spectrum",)` continuous musical dynamics from soft intros (`~36%`) to loud brass swells (`~96%`) while keeping a `25%` floor so stars remain visible on crisp transient attacks even before smoothed band energy peaks.

---

## 6. Open Items & Next Steps

* [ ] Proceed with the planned Law 7 mode redesign batches (`Middle_bar_mode`, `Chromatic_chaser_mode`, `Extending_waves_mode`, `Rainbow_mode`, `Proportion_rainbow_mode`) and promote each batch into `CONFORMING_MODES_PHASE_4A`.
