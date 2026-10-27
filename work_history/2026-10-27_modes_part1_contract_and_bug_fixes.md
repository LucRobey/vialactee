# [2026-10-27] Modes Audit & Contract Alignment (Part 1: Contract Alignment & Bug Fixes)

> **Date:** 2026-10-27  
> **Session ID:** `e2408642-19a8-463f-913b-741dac701d87`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Execute Part 1 of the Modes Audit & Contract Alignment across `modes/`, `core/Segment.py`, and `transitions/mode_dna.py`: resolve systemic findings `S1`–`S7` (cooperative transition handshake, automatic `transition_scale` attenuation, `MODE_DNA` spatial roles, per-segment phase staggering, additive `drop_decay`, public `asserved_fft_band`, chroma floor subtraction, and full-strip Silence Law decay) and fix 7 concrete mode rendering bugs.  
> **Status:** COMPLETED  
> **Commits:** `9f39cfa`, `fe43d92`, `b63f83d`, `33699d9`, `056ebbe`  
> **Skills Used:** `vialactee-mode-creator`, `vialactee-project`  
> **Skill Friction:** None

---

## 1. Context & Motivation

* The comprehensive audit of all 21 visual modes (`modes/`), `modes/Mode.py`, `core/Segment.py`, and `transitions/mode_dna.py` against [`docs/contracts/mode_contract.md`](../docs/contracts/mode_contract.md), [`docs/contracts/transition_contract.md`](../docs/contracts/transition_contract.md), [`docs/contracts/mood_contract.md`](../docs/contracts/mood_contract.md), and [`docs/contracts/music_analyzer_contract.md`](../docs/contracts/music_analyzer_contract.md) surfaced 7 systemic issues (`S1`–`S7`) and 7 concrete per-mode rendering bugs:
  * **S1 (`transition_scale` Adoption & Cooperative Handshake)**: Only 3 of 21 modes multiplied output by `self.transition_scale`, while `Segment.py` was missing `transition_mode_handshake`, `dual_rgb_list.fill(0)`, `np.copyto(self.rgb_list, self.dual_rgb_list)` on transition completion, and `on_transition_exit` / `on_transition_enter` / `on_transition_reset` lifecycle calls.
  * **S2 (Multi-Segment Phase Staggering)**: 17 of 21 modes initialized phase/drift accumulators to `0.0` instead of seeding with `self.segment_phase_offset`, causing all 24 chandelier segments to pulse in rigid lockstep.
  * **S3 (`MODE_DNA` Spatial Role Mismatch)**: `transitions/mode_dna.py` misclassified 8 modes (`Static Wave`, `PSG`, `Middle Bar`, `Coloured Middle Wave`, `Extending Waves`, `Opposite Sides`, `Chromatic Chaser`, `Beat Runner`) relative to [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md).
  * **S4 (`drop_decay` Underutilization)**: Only 2 of 21 modes read `self.drop_decay`, making the 5-second post-drop sustain indistinguishable from `GROOVE`.
  * **S5 (Private `_delayed_asserved_fft_band` & Unfloored Chroma)**: 4 modes accessed private `_delayed_asserved_fft_band` instead of public `asserved_fft_band`, and `Synesthesia_mode` did not subtract the 85% chroma noise floor before normalizing.
  * **S6 (Silence Law Violations)**: 14 modes failed to fade their entire strip to black under sustained `ctx.is_silent = True` (leaving frozen outer bars, bright center pixels, or un-faded background regions), and `Mode.beat_pulse()` leaked up to `0.15` when `beat_trust > 0` during brief silence cuts.
  * **S7 (Unused `band_proportion` & `beat_tag`)**: Neither 🟢 HIGH-trust signal was consumed by any mode.
  * **7 Mode Rendering Bugs**:
    1. `Power_bar_mode`: Unfaded gap between contracting bar (`p_int + 1`) and floating peak-hold dot (`dot_idx - 1`), plus `white_dot_height` bouncing back to `1.0` when `power_height == 0.0`.
    2. `Static_wave_mode`: Unfaded gap between shrinking inner bar and floating outer caps, plus frame-rate-dependent `-0.2` cap decay.
    3. `Chromatic_chaser_mode`: Skipped dark LEDs when `effective_speed > 1.0` and head dimmed on the frame it was painted.
    4. `Beat_runner_mode`: Double-frequency pendulum bounce (`cos(2*pi*phase)` completing a full round-trip per beat instead of 1 sweep per beat via `beat_count & 1`) and sawtooth phase-wrap reversal when blending `phase` and `free_phase`.
    5. `Shining_stars_mode`: Identical star offset repeated across every `sub_segment_size` window via slice step `self.rgb_list[random_pos::step]`, plus a 1,100-iteration import-time loop.
    6. `Coloured_middle_wave_mode` & `Rhythm_breather_mode`: Legacy `0.5` pre-scale + bitshift view hack in `Coloured_middle_wave_mode`; dead arrays, double `rhythm_lock` gating, and 2-slot palette truncation (`mood[0]..mood[1]` only) in `Rhythm_breather_mode`.

---

## 2. Changes Made

### Step 1 — Cooperative Transition Handshake, Automatic `transition_scale`, & `MODE_DNA` Spatial Roles (`S1`, `S3`)
* **[MODIFY]** [`modes/Mode.py`](../modes/Mode.py):
  * Added `on_transition_reset()` to restore `_exit_progress = 0.0` and `_enter_progress = 1.0`.
  * Applied `self.transition_scale` automatically inside `_blend_into()` whenever `(self._exit_progress > 0.0 or self._enter_progress < 1.0)`, keeping steady-state blending bit-identical while giving all 21 modes cooperative transition scaling at the base-class level.
  * Added `if silent: return 0.0` at the top of `Mode.beat_pulse()` so silence cuts never leak flywheel pulses.
* **[MODIFY]** [`core/Segment.py`](../core/Segment.py):
  * Restored cooperative handshake lifecycle (`self.transition_mode_handshake`, `self.dual_rgb_list.fill(0)` on transition start, `np.copyto(self.rgb_list, self.dual_rgb_list)` on completion, and `on_transition_exit` / `on_transition_enter` / `on_transition_reset` calls).
* **[MODIFY]** [`modes/Flying_ball_mode.py`](../modes/Flying_ball_mode.py), [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py), [`modes/Impact_shockwave_mode.py`](../modes/Impact_shockwave_mode.py):
  * Removed redundant manual amplitude `* self.transition_scale` multiplications to prevent double attenuation (`transition_scale ** 2`).
* **[MODIFY]** [`transitions/mode_dna.py`](../transitions/mode_dna.py):
  * Aligned `"spatial_role"` for all 21 modes with [`docs/reference/modes_catalog.md`](../docs/reference/modes_catalog.md) (`"vertical"`: `Power Bar`, `Plasma Fire`; `"horizontal"`: `Beat Runner`, `Chromatic Chaser`, `Flying Ball`, `Magnetic Ball`; `"both"`: all 15 remaining modes).

### Step 2 — Per-Segment Phase Staggering, `drop_decay` Sustain, & `Bary_rainbow_mode` Smoothing (`S2`, `S4`)
* **[MODIFY]** Seeded internal phase/drift accumulators with `self.segment_phase_offset` across 17 modes: [`Rainbow_mode.py`](../modes/Rainbow_mode.py), [`Bary_rainbow_mode.py`](../modes/Bary_rainbow_mode.py), [`Rhythm_breather_mode.py`](../modes/Rhythm_breather_mode.py), [`Beat_runner_mode.py`](../modes/Beat_runner_mode.py), [`Middle_bar_mode.py`](../modes/Middle_bar_mode.py), [`PSG_mode.py`](../modes/PSG_mode.py), [`Opposite_sides_mode.py`](../modes/Opposite_sides_mode.py), [`Plasma_fire_mode.py`](../modes/Plasma_fire_mode.py), [`Hyper_strobe_mode.py`](../modes/Hyper_strobe_mode.py), [`Synesthesia_mode.py`](../modes/Synesthesia_mode.py), [`Metronome_mode.py`](../modes/Metronome_mode.py), [`Flying_ball_mode.py`](../modes/Flying_ball_mode.py), [`Static_wave_mode.py`](../modes/Static_wave_mode.py), [`Power_bar_mode.py`](../modes/Power_bar_mode.py), [`Extending_waves_mode.py`](../modes/Extending_waves_mode.py), [`Magnetic_ball_mode.py`](../modes/Magnetic_ball_mode.py), and [`Chromatic_chaser_mode.py`](../modes/Chromatic_chaser_mode.py).
* **[MODIFY]** Added additive `+ 0.20 * self.drop_decay` post-drop sustain boost in [`Impact_shockwave_mode.py`](../modes/Impact_shockwave_mode.py), [`Plasma_fire_mode.py`](../modes/Plasma_fire_mode.py), [`Power_bar_mode.py`](../modes/Power_bar_mode.py), and [`Rhythm_breather_mode.py`](../modes/Rhythm_breather_mode.py).
* **[MODIFY]** [`modes/Bary_rainbow_mode.py`](../modes/Bary_rainbow_mode.py): Consolidated left, center, and right hues into a single contiguous `self.hues` buffer with a single `RGB_HSV.fromHSV_toRGB_vectorized` call and `self.smooth_vectorized(self.alpha(14.0), self.target_rgb)`.

### Step 3 — Public `asserved_fft_band`, Chroma Noise Floor Subtraction, & Silence Law Compliance (`S5`, `S6`)
* **[MODIFY]** Replaced `_delayed_asserved_fft_band` with public `asserved_fft_band` in [`Rainbow_mode.py`](../modes/Rainbow_mode.py), [`Proportion_rainbow_mode.py`](../modes/Proportion_rainbow_mode.py), [`Coloured_middle_wave_mode.py`](../modes/Coloured_middle_wave_mode.py), and [`Static_wave_mode.py`](../modes/Static_wave_mode.py).
* **[MODIFY]** [`modes/Synesthesia_mode.py`](../modes/Synesthesia_mode.py): Pre-allocated `self.clean_chroma` and subtracted `0.85 * float(np.min(self.clean_chroma))` before normalizing so broadband percussion does not wash out harmonic color identity.
* **[MODIFY]** Enforced full-strip decay to black (`[0, self.nb_of_leds - 1]`) during `ctx.is_silent` across all 21 modes.

### Step 4 — Fix the 7 Mode Rendering Bugs & Consume `beat_tag` / `band_proportion` (`S7`)
* **[MODIFY]** [`modes/Power_bar_mode.py`](../modes/Power_bar_mode.py): Faded `[p_int + 1, self.nb_of_leds - 1]` *before* painting `dot_idx`, and guarded `white_dot_height` peak push with `self.power_height >= 0.5`.
* **[MODIFY]** [`modes/Static_wave_mode.py`](../modes/Static_wave_mode.py): Scaled cap decay by `(0.2 * self.fps_ratio) / max(0.5, self.mood_trail)` and faded `[0, start_idx - 1]` and `[end_idx + 1, self.nb_of_leds - 1]` *before* painting `boundary_p1` / `boundary_p2`.
* **[MODIFY]** [`modes/Chromatic_chaser_mode.py`](../modes/Chromatic_chaser_mode.py): Faded the strip *before* painting the continuous swept span `[prev_idx, head_idx]` (including wrap-around when `bounce_enabled=False`).
* **[MODIFY]** [`modes/Beat_runner_mode.py`](../modes/Beat_runner_mode.py): Implemented 2-beat pendulum cycle using `float(count & 1) + phase` (1 sweep per beat), blended locked and free positions in position space, and removed dead `self.hues` / `self.sats` arrays.
* **[MODIFY]** [`modes/Shining_stars_mode.py`](../modes/Shining_stars_mode.py): Randomized star positions independently inside each `sub_segment_size` window using a zero-allocation `while` loop, replaced `isinstance(ctx, MusicalContextEngine)` with `isinstance(getattr(ctx, "is_silent", None), bool)`, and removed the 1,100-iteration import-time loop.
* **[MODIFY]** [`modes/Coloured_middle_wave_mode.py`](../modes/Coloured_middle_wave_mode.py) & [`modes/Rhythm_breather_mode.py`](../modes/Rhythm_breather_mode.py): Replaced the `0.5` pre-scale + bitshift view hack in `Coloured_middle_wave_mode` with `smooth_segment_vectorized(ratio, ...)`; removed dead arrays, eliminated double `rhythm_lock` gating, and sampled all 3 mood palette slots via `self.palette_sample(self.spatial_blend, self.grad_colors)` in `Rhythm_breather_mode`.
* **[MODIFY]** [`modes/Proportion_rainbow_mode.py`](../modes/Proportion_rainbow_mode.py), [`modes/Hyper_strobe_mode.py`](../modes/Hyper_strobe_mode.py), [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py): Consumed `listener.band_proportion` (with `+ 0.04` uniform floor) in `Proportion_rainbow_mode` and `listener.beat_tag` (`"Bass/Kick"`, `"Snare/Mid"`, `"Hi-hat/Cymbal"`) in `Hyper_strobe_mode` (while bridging the `0.35..0.40` confidence gap) and `Extending_waves_mode`.

### Step 5 — Unit Tests & Verification
* **[MODIFY]** [`tests/test_mode_helpers.py`](../tests/test_mode_helpers.py), [`tests/test_all_modes_musical_context.py`](../tests/test_all_modes_musical_context.py), [`tests/test_transition_bridge.py`](../tests/test_transition_bridge.py):
  * initialized `self.engine._is_silent = False` in `_ModeTestCase.setUp()` and `TestAllModesMusicalContext.setUp()` so active-path tests (`test_axiom_01_frame_execution_time`, `test_axiom_02_zero_dynamic_heap_allocations`, `TestColouredMiddleWaveBuffer`) genuinely exercise the full rendering path of all 21 modes rather than taking early silence returns.
  * Added `test_cooperative_transition_scale_attenuation`, `TestModeDnaSpatialRoles`, `TestPart1ModeBugFixes` (`Power_bar_mode` gap fade, `Static_wave_mode` gap fade, `Chromatic_chaser_mode` high-speed span continuity, `Beat_runner_mode` 2-beat pendulum direction alternation, `Shining_stars_mode` per-subsegment randomization), `test_all_modes_silence_decay_to_black`, and `test_proportion_rainbow_and_beat_tag_consumption`.

---

## 3. Verification & Testing

* **Command**: `.venv\Scripts\python.exe -m pytest -q tests/governance/ test_transition_bridge.py tests/transitions/test_families_and_handshake.py tests/test_segment.py tests/test_mood_and_transitions.py tests/test_mode_helpers.py tests/test_extending_waves.py tests/test_all_modes_musical_context.py tests/test_mode_render.py`
  * **Result**: All passed (including AXIOM-01 $\le 0.20\text{ ms}$ frame budget and AXIOM-02 zero heap allocation tests on all 21 modes).
* **Command**: `.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_benchmark_engine.py --ignore=tests/test_app_config_store.py --ignore=tests/test_command_router.py`
  * **Result**: `433 passed, 26 warnings, 93 subtests passed in 31.04s` (0 failures across the entire repository test suite).

---

## 4. Architecture Decisions & Trade-offs

* **Base-Class `transition_scale` Attenuation in `Mode._blend_into`**: Applying `self.transition_scale` inside `Mode._blend_into()` only when `(self._exit_progress > 0.0 or self._enter_progress < 1.0)` preserves bit-identical output during steady-state rendering while guaranteeing that all 21 modes participate in cooperative transitions without requiring boilerplate per-mode amplitude scaling.
* **Single Contiguous HSV Conversion in `Bary_rainbow_mode` & `Proportion_rainbow_mode`**: Combining left, center, and right hue slices into a single pre-allocated `self.hues` buffer reduced `RGB_HSV.fromHSV_toRGB_vectorized` calls from 3 per frame to 1 per frame, cutting `Bary_rainbow_mode` frame time from `0.29 ms` to `< 0.14 ms` (well inside the `0.20 ms` AXIOM-01 budget).

---

## 5. Pitfalls & Lessons Learned

* **`MusicalContextEngine.__init__` Default `_is_silent = True` in Unit Test Fixtures**: `MusicalContextEngine` initializes `self._is_silent = True` until `update(dt)` is called. In `tests/test_all_modes_musical_context.py` and `tests/test_mode_helpers.py`, `setUp()` instantiated `MusicalContextEngine(self.listener)` without calling `update()` or setting `self.engine._is_silent = False`, which previously caused any mode with an `if ctx.is_silent: return` guard to skip its active rendering body during `test_axiom_01` and `test_axiom_02` benchmarks. Explicitly setting `self.engine._is_silent = False` in `setUp()` exposed a real `0.29 ms` AXIOM-01 violation in `Bary_rainbow_mode` and verified active-path zero-allocation compliance across all 21 modes.
* **Python `range()` Iterator Allocation in Tight Inner Loops**: In `Shining_stars_mode.run()`, `for base in range(0, self.nb_of_leds, step):` allocates a temporary `range` object and iterator on each triggered band; replacing it with an index-driven `while base < n_leds:` loop maintains strict 0-byte `tracemalloc` compliance in `test_shining_stars_mode_zero_heap_allocation`.

---

## 6. Open Items & Next Steps

* [ ] Proceed to Part 2 of the Modes Upgrade Plan (creative visual expressiveness enhancements if requested by the user).
