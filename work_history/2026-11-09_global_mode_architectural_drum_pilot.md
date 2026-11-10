# 2026-11-09 Global Mode Infrastructure & 5 Spatial Global Modes

> **Date:** 2026-11-09  
> **Session ID:** `503ac578-16b8-43d8-a130-faa9b92a9f37`  
> **Agent / Model:** Gemini 4 Argon (High)  
> **Primary Goal:** Design and prototype mixed Global + Per-Segment mode orchestration (`IS_GLOBAL = True`, `utils/global_mode.py`) and deliver 5 spatial Global Modes (`Architectural Drum`, `Synaptic Grid`, `Tilt Tank`, `Prism Lighthouse`, `Attractor Orb`).  
> **Status:** COMPLETED  
> **Commits:** `115558e` (pushed: yes)  
> **Skills Used:** `vialactee-project`, `vialactee-mode-creator`, `vialactee-dsp-engine`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The user wanted to explore **Global Modes** that orchestrate all 11 segments of the chandelier as a single unified visual instrument in a **mixed** architecture (coexisting with per-segment modes), first prototyping `Architectural Drum` and then spawning 4 parallel subagents to build 4 original 2D/topological Global Modes (`Synaptic Grid`, `Tilt Tank`, `Prism Lighthouse`, `Attractor Orb`).

---

## 2. Changes Made

### Global Mode Spatial & Role Resolver
* **[NEW]** [`utils/global_mode.py`](../utils/global_mode.py):
  * Added `SegmentSpatialProfile` to resolve canonical segment IDs (`v1..v4`, `h00..h32`, `s1..s3`), architectural roles (`"pillar"`, `"bridge"`, `"canopy"`, and `"composite"` for 1D studio/test preview strips), tiers (`"canopy"`, `"mid"`, `"low"`), halves (`"left"`, `"right"`), and pre-allocated 2D normalized room coordinates (`x_norm`, `y_norm`, `altitude`) + strip coordinates (`u`, `u_center`) with zero runtime heap allocations.

### 5 Global Modes (`modes/` & `config/modes.json`)
* **[NEW]** [`modes/Architectural_drum_mode.py`](../modes/Architectural_drum_mode.py) (`"Architectural Drum"`, `LEAD = "spectrum"`, `SECONDARY = ("beat",)`):
  * Decomposes the 16-band Mel spectrum and beat stream across 3 physical zones of the chandelier:
    1. **Vertical Pillars (`v1–v4`, role `"pillar"`):** Bass & Kick hydraulic pistons (`sub_bass` on inner pillars `v2/v3`, `upper_bass` on outer pillars `v1/v4`) with falling gravity crowns.
    2. **Horizontal Bridges (`h10, h11, h31, h32`, role `"bridge"`):** Snare & mid-range center-outward shockwaves modulated by outward traveling phase ripples and `spectral_tilt`.
    3. **High Canopy (`h00, h20, h30`, role `"canopy"`):** Continuous 432-column room-X panoramic aurora driven by treble bands (`10..15`) and `vertical_center` with constructive-interference hi-hat diamond sparkles.
* **[NEW]** [`modes/Synaptic_grid_mode.py`](../modes/Synaptic_grid_mode.py) (`"Synaptic Grid"`, `LEAD = "beat"`, `SECONDARY = ("spectrum",)`):
  * Routes 3 staggered Tron light-cycle cascades across the exact connected 2D wiring topology of all 11 segments (`v2 -> h10 -> v1 -> h00`, `v2 -> h11 -> v1`, `v2 -> h20 -> h30`, `v3 -> h31/h32 -> v4` bidirectional splits) and ignites localized Gaussian highlight flares at every physical segment intersection.
* **[NEW]** [`modes/Tilt_tank_mode.py`](../modes/Tilt_tank_mode.py) (`"Tilt Tank"`, `LEAD = "spectrum"`, `SECONDARY = ("beat",)`):
  * Treats the entire `432 x 246` room as a 2D glass tank of sloshing bioluminescent liquid whose surface horizon `surface_alt(x)` rises with the 16-band Mel spectrum and `vertical_center`, tilts diagonally across room width `x_norm` with `spectral_tilt * tilt_gain` and beat-locked sloshing, and crowns the tilted meniscus with a glowing foam crest (`crest_glow`) and upward spray droplets.
* **[NEW]** [`modes/Prism_lighthouse_mode.py`](../modes/Prism_lighthouse_mode.py) (`"Prism Lighthouse"`, `LEAD = "beat"`, `SECONDARY = ("transient",)`):
  * Maps every LED into 2D polar coordinates `(radius, angle)` around the chandelier's architectural core `(cx = 0.62, cy = 0.45)`, sweeping two counter-rotating prism searchlight beams across `angle` in lock-step with `beat_phase` / `beat_pulse()` while firing expanding 2D radial sonar shockwaves across `radius` on `is_real_beat`, `drop_hit`, and bass `band_flux` bursts.
* **[NEW]** [`modes/Attractor_orb_mode.py`](../modes/Attractor_orb_mode.py) (`"Attractor Orb"`, `LEAD = "level"`, `SECONDARY = ("spectrum",)`):
  * Moves a 2D plasma sphere and counter-orbiting satellite along a smooth Lissajous figure-8 trajectory `(orb_x, orb_y)` across normalized room space, illuminating nearby segments via true 2D Euclidean distance `d^2` with `level`-driven supernova radius/brightness and `spectrum`-driven vertical altitude (`vertical_center`) + corona shimmer.

### Mixed Orchestration, Unison Activation & Desktop Panel Global Mode Picker
* **[MODIFY]** [`modes/Mode.py`](../modes/Mode.py):
  * Added class attribute `IS_GLOBAL: bool = False` on `Mode`.
* **[MODIFY]** [`config/modes.json`](../config/modes.json):
  * Added `"global_modes"` registry entries for `"Architectural Drum"`, `"Synaptic Grid"`, `"Tilt Tank"`, `"Prism Lighthouse"`, and `"Attractor Orb"`.
* **[MODIFY]** [`core/Segment.py`](../core/Segment.py):
  * Loaded `mode_config.get("global_modes", [])` alongside `standard_modes`, bound segment geometry (`id`, `orientation`, `tags`, `coords_array`) via `bind_segment_geometry`, and enforced physical `UP` index ordering in `update_leds()` when `IS_GLOBAL` is active so 2D coordinates and vertical pillars are never inverted.
* **[MODIFY]** [`core/TransitionBridge.py`](../core/TransitionBridge.py), [`core/Mode_master.py`](../core/Mode_master.py) & [`core/CommandRouter.py`](../core/CommandRouter.py):
  * Added `sync_mode_scope()` and `apply_panel_command()` (`set_locked`, `set_segment_mode`, `set_global_mode`, `set_mode_scope`) so switching to Global scope puts all 11 segments on the selected Global Mode in unison and configures the transition sector (`whole-installation` unison policy + `"global_modes"` profiles) to transition between Global Modes, while switching to Local scope restores per-segment local mode casting.
* **[MODIFY]** [`hardware/VisualizerHud.py`](../hardware/VisualizerHud.py):
  * Expanded the **SHOW CONTROL** panel (`CONTROL_PANEL_H = 175`) with:
    1. **MODE SCOPE Toggle (`_rect_scope`, Hotkey `G`):** Switches between `GLOBAL (All Segments)` and `LOCAL (Per-Segment)`.
    2. **Global Mode Picker (`<` `[ GLOBAL [i/5]: <Mode> ]` `>`):** Cycles all 11 segments through the 5 Global Modes in unison (`set_global_mode`).
    3. **Local-Only Segment Arrows:** Per-segment `<` `>` buttons in `SEGMENT MODES` now filter out `global_modes` so local picks only cycle the 13 local modes.
    4. **Visual Indicator:** Active Global Modes in `SEGMENT MODES` render in warm gold (`(255, 195, 110)`).

### Verification Suite
* **[NEW/MODIFY]** [`tests/test_global_modes.py`](../tests/test_global_modes.py) & [`tests/test_panel_show_control.py`](../tests/test_panel_show_control.py):
  * Added unit and governance tests covering all 5 Global Modes across architectural role resolution, 2D rendering, flywheel-lost resilience, silence decay, AXIOM-01 (`<= 0.20 ms`), AXIOM-02 (0 heap allocations), Law 7 lead dominance, and desktop panel Global/Local mode scope + Global Mode `<` `>` picker.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/test_panel_show_control.py tests/test_global_modes.py tests/governance/ -q`
  * **Result**: 77 passed, 61 subtests passed, 0 failed.
* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/test_global_modes.py tests/test_all_modes_musical_context.py tests/test_mode_helpers.py tests/governance/ -q`
  * **Result**: 100 passed, 61 subtests passed, 0 failed.

---

## 4. Architecture Decisions & Trade-offs

* **Decision 1 (Mixed Role-Aware `Mode` Subclassing + `utils/global_mode.py`):** Keeping Global Modes as `Mode` subclasses with `IS_GLOBAL = True` and pre-bound `SegmentSpatialProfile` allows all 29 existing dual-buffer transitions (`explosion`, `supernova`, `liquid_geyser`, etc.) to transition seamlessly between per-segment mixes and Global Modes with zero special-casing in `Segment.update()`.
* **Decision 2 (`"global_modes"` section in `config/modes.json`):** Separating `"global_modes"` from `"standard_modes"` in `config/modes.json` preserves the 13-mode invariant for per-segment coherence casting while making all 5 Global Modes available across all segments in `Segment.py`, `Main.py`, `VisualizerHud.py`, and `mode_studio.py`.

---

## 5. Pitfalls & Lessons Learned

* `Segment.update_leds()` reverses LED index order when `self.way == "DOWN"`. For Global Modes (`IS_GLOBAL = True`), `update_leds()` must bypass `self.way == "DOWN"` reversal so all 4 vertical pillars (`v1..v4`) shoot upward from the floor in unison and horizontal coordinates match true 2D room space.
* Keep large constant topology lookup tables compact so production mode files remain comfortably under the 500-line AXIOM-07 governance cap (`modes/Synaptic_grid_mode.py` trimmed from 509 to 458 lines).

---

## 6. Open Items & Next Steps

* [ ] Playtest all 5 Global Modes live in the Simulator (`Main.py --song --mode "<Mode Name>" --panel`) and `mode_studio.py`.
* [ ] Decide how automatic transitions (`transitions/`) should schedule Global Modes alongside per-segment zone casts.
