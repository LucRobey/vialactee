# [2026-11-02] Extending Waves — Balanced Wavelength Stream & Red Drum Peaks

> **Date:** 2026-11-02  
> **Session ID:** `5670a1f5-f9e2-4e10-b5b0-622b92fce8f9`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Rework `Extending_waves_mode` into a continuous center-outward scrolling wavelength stream with balanced multi-band color evolution and regular Red drum peaks at a steady outward speed.  
> **Status:** COMPLETED  
> **Commits:** `ac2662a` `aed3f76` `bbe4da9` (pushed: yes)  
> **Skills Used:** `vialactee-mode-creator`, `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The user noted that [`Extending_waves_mode`](../modes/Extending_waves_mode.py) was visually too monochromatic ("always the same color") because it relied on a single mood-palette bed and a 3-slot mood color cycle driven by a scalar `level` accumulator.
* The user requested:
  1. **Continuous center-outward scrolling wave stream:** Colors move regularly from center to edges so the listener can visually see the music evolving as a moving timeline.
  2. **Balanced dominant wavelength color (`0.00` Red $\to$ `0.82` Violet):** Colors match the most important playing wavelength (`asserved_fft_band` + `band_flux`), balanced via per-band rolling-mean deviation, spectral attack, 1/f high-band equalization, and anti-stagnation fatigue so colors change frequently across all 8 bands.
  3. **Regular Red drum peaks:** Drum/kick hits in Band 0 punch through as vivid Red peaks (`hue = 0.00`) that extend outward at a steady, volume-independent pace and immediately yield to melodic/harmonic wavelengths between beats.

---

## 2. Changes Made

### Mode Implementation
* **[MODIFY]** [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py):
  * Updated choreography declaration to `LEAD = "spectrum"` and `SECONDARY = ("transient",)`.
  * Precomputed a 256-entry vivid rainbow LUT (`self.rainbow_lut`, hues `0.00` Red $\to$ `0.82` Violet) and pre-allocated a zero-diffusion subpixel circular history buffer (`self.hist_rgb`) plus vectorized interpolation scratch buffers (`_src_pos`, `_src_floor`, `_src_frac_2d`, `_idx0`, `_idx1`, `_sample0`, `_sample1`, `_radial_env_2d`) for zero runtime heap allocations (AXIOM-02).
  * Implemented balanced dominant wavelength scoring across all FFT bands (`_band_dev` rolling EMA deviation, `_band_rise` positive attack, `_rel_bands` mean-rebalanced band share, `_norm_flux` normalized onset flux, `band_eq` 1/f high-band equalization, `_band_fatigue` anti-stagnation habituation, and `_band_hold_time` hysteresis).
  * Added rising-edge drum peak detection (`_drum_hold_frames = 4`, `_drum_cooldown`, post-drum Band 0 fatigue boost) so drum hits inject crisp Red (`hue = 0.00`) crests and immediately hand off to melodic bands.
  * Added sound-power intensity scaling (`sound_drive` from `max_band` and `ctx.energy`) and locked `beat_phase` modulation (`phase_crest = phase_wave ** 1.5`, `rhythm_env = 0.22 + 0.78 * phase_crest`, weighted by `lock_weight = min(1.0, lock / 0.45) * self._spec_activity`), producing `~4.2–4.5x` peak-to-valley intensity contrast between `beat_phase ~ 1.0/0.0` (very intense center light) and `beat_phase ~ 0.5` (visible low valley) when the beat is locked.
  * Preserved discrete travelling wave crests (`MAX_WAVES = 8`) and bespoke cooperative exit white-wave stacking (`self._stack_frontier`).

### Catalog, Configuration & Tests
* **[MODIFY]** [`config/modes.json`](../config/modes.json):
  * Updated `Extending Waves` tags to `["lead:spectrum", "axis:horizontal", "form:wave", "origin:center", "color:own-hue", "layer:meter"]`.
* **[MODIFY]** [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md):
  * Updated row 13 (`Extending Waves`) Lead (`spectrum`), Secondary (`transient`), visual description, and Section 4 `tags` to match the code.
* **[MODIFY]** [`tests/test_extending_waves.py`](../tests/test_extending_waves.py):
  * Replaced legacy `level_accum` tests with 8 behavioral tests covering Red drum peaks, full-spectrum wavelength mapping (`b=0` Red, `b=4` Green/Cyan, `b=7` Blue/Violet), anti-stagnation band rotation, post-drum melodic handoff, volume-independent steady scroll speed, outward propagation in `BUILDUP`, center symmetry, and silence decay.

---

## 3. Verification & Testing

* **Unit, Governance & Transition Handshake Tests**:
  * Command: `.\.venv\Scripts\python.exe -m pytest tests/governance/ tests/test_all_modes_musical_context.py tests/test_extending_waves.py tests/transitions/test_families_and_handshake.py -q -p no:cacheprovider`
  * Result: `84 passed, 6 subtests passed`.
* **Synthetic Choreography Matrix (`high_lock`, `groove_lock`, `loose_lock`)**:
  * Result: `R_std = 58.84`, `f = 0.99 >= 0.30`, `g = 0.95 >= 0.65`, contributions `{'beat': 0.0, 'level': 0.0, 'spectrum': +58.52, 'transient': +3.19}`.
* **Real-Audio Choreography Probe (`tools/choreography_probe.py`)**:
  * `01-Plastic-People.mp3`: `R_std(full) = 52.75`, `f = 0.94`, `g = 0.98`, band win % `[22.2, 15.9, 16.3, 13.5, 5.7, 5.4, 9.8, 11.3]`, `11.68 switches/sec`.
  * `Another One Bites The Dust - Remastered 2011.mp3`: `R_std(full) = 47.41`, `f = 0.91`, `g = 0.88`, band win % `[21.0, 11.8, 9.4, 9.5, 8.8, 7.9, 7.5, 24.1]`, `10.08 switches/sec`.

---

## 4. Architecture Decisions & Trade-offs

* **Decision 1 (Lagrangian Circular History Buffer vs. Eulerian Strip Advection):** Advecting an LED buffer onto itself at subpixel speeds (`< 1.0` LED/frame) via linear interpolation introduces severe numerical diffusion that blurs 3-LED Red drum peaks into neighboring colors within ~20 frames. Sampling a circular history buffer (`self.hist_rgb`) at `self.scroll_pos - self.half_coords` achieves subpixel smoothness with **zero numerical diffusion**.
* **Decision 2 (Drum Hold + Post-Drum Fatigue Injection):** Raw audio has natural $1/f$ low-frequency energy that can cause Band 0 to dominate `> 40%` of frames if scored naively. Combining a 4-frame rising-edge drum peak hold (`_drum_hold_frames = 4`) with a beat-scaled cooldown (`_drum_cooldown`) and an immediate post-drum fatigue increment (`_band_fatigue[0] += 1.10`) guarantees crisp Red drum peaks (`~21–22%` of frames) that immediately yield to Orange, Green, Cyan, Blue, and Violet bands between hits.

---

## 5. Pitfalls & Lessons Learned

* **Big-Beat Saturation Reset & Inter-Beat Silence Pocket Lag:**
  1. On loud beats (e.g. `Palladium.mp3`, `Another One Bites The Dust`), all 8 bands of `asserved_fft_band` can clip at `[1.0, ..., 1.0]` for 5–8 frames. Any `max_abs_delta < 1e-6` static-spectrum detector that resets `self.hist_rgb[:] = self._center_rgb` or zeroes `_spec_activity` will falsely trigger on saturated big beats and wipe the entire strip to black. Removing the mid-song `hist_rgb` reset and blending unclipped `band_proportion` (`0.28 * p_scaled`) into `self.fft_bands` preserves inter-band contrast and continuous frame-to-frame motion even when `asserved_fft_band` saturates at `1.0`.
  2. Immediately after a big beat, `AudioIngestion.total_power_gm` jumps to `1.01 * smoothed_total_power`, which can push `asserved_total_power < 0.05` (`ctx.is_silent = True`) for 5–20 frames in the rhythmic pocket between beats. Early-returning and decaying `hist_rgb *= 0.75` on Frame 1 of `is_silent` froze `scroll_pos` (visual lag) and erased travelling waves. Holding normal outward scrolling across brief pockets (`self._silent_frames <= 22`) and only fading to black on sustained silence (`> 22` frames) reduced `scroll_stopped` and `strip_blackouts` to `0` across all 2400 evaluation frames on `Palladium.mp3`, `01-Plastic-People.mp3`, and `Another One Bites The Dust`.
* **Cooperative Exit Center Whitening:** When whitening `_center_rgb` during cooperative exit (`_exit_progress > 0.0`), whitening the hue first and then scaling by `center_val * center_exit_atten` preserves the outer-to-inner white stacking invariant tested by `test_extending_waves_bespoke_white_wave_stacking_on_exit`.

---

## 6. Open Items & Next Steps

* [ ] Visual evaluation in Mode Studio (`python tools/mode_studio.py`) by the user on preferred tracks to fine-tune outward scroll pace or drum sensitivity if desired.
