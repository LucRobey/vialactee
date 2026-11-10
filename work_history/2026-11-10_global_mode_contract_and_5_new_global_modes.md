# 2026-11-10 Global Mode Contract & 5 High-Legibility Global Audio Modes

> **Date:** 2026-11-10  
> **Session ID:** `75b93199-1cbb-40bc-856a-4852ff7fef22` & `ddd3383f-96c7-451f-9877-d8a9e115c9cb`  
> **Agent / Model:** Gemini 4 Argon (High)  
> **Primary Goal:** Establish the rigid [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md) (5 Doors, Laws 1–10), author the master perceptual research report, replace the complex initial global mode prototypes in `config/modes.json` with 5 immediately legible, ultra-bright, monolithic global audio modes built in parallel by 5 specialized subagents, and integrate desktop/studio Mood & Show Control enhancements.  
> **Status:** COMPLETED  
> **Commits:** pending (pushed: no)  
> **Skills Used:** `vialactee-project`, `vialactee-mode-creator`, `vialactee-dsp-engine`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The 5 initial global mode prototypes (`Architectural Drum`, `Synaptic Grid`, `Tilt Tank`, `Prism Lighthouse`, `Attractor Orb`) suffered from "The Display Fallacy" (treating a sparse 1,304-LED 3D chandelier with `< 2%` fill factor as a 2D bitmap display), multi-role cognitive fragmentation (splitting pillars, bridges, and canopy into competing sub-modes), crossmodal binding collapse, and linear RGB gray mud.
* We conducted a multi-agent `/teamwork` deep-thinking & perceptual research phase (`2d5c51dc-ce07-4e59-8071-9a84f98bf7cf`), authored a rigid [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md) (5 Doors, Laws 1–10) and [`docs/research/2026-11-09_global_audio_modes_research_and_design.md`](../docs/research/2026-11-09_global_audio_modes_research_and_design.md), and then dispatched 5 parallel subagents (`e282236e`, `8311149c`, `5d03b37a`, `b4ad7c81`, `00b73c78`) to implement and verify the 5 new Global Modes.

---

## 2. Changes Made

### Contracts & Research Documentation
* **[NEW]** [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md):
  * Defines the **5 Doors of Global Modes** (Audio & Musical Context, Mood Palette & Modifiers, Transition Handshake & `IS_GLOBAL = True`, Sanctioned Gated Helpers, and `SegmentSpatialProfile` across 1,304 LEDs / 11 segments) and **10 Architectural and Perceptual Laws (Laws 1–10)**:
    * **Law 1:** Universal Flywheel Resilience (continuous acoustic fallback when `rhythm_lock == 0.0`, tight phase-lock when `rhythm_lock -> 1.0`, phase-wrap protection, and ballistic state drain in silence).
    * **Law 2:** Subtle Mood Governance (zero `ctx.scene` branching).
    * **Law 3:** Transient Physics (1-frame spikes vs multi-frame `drop_decay` envelopes, white-crest highlight rule).
    * **Law 4:** Palette Gradient Lookup & Anti-Mud Law ($S \ge 0.92$, $V_{\text{active}} \ge 0.85$, pure black `(0, 0, 0)` unlit ground).
    * **Law 5:** Settings Schema Honesty (every declared setting actively consumed in `run()`).
    * **Law 6:** Zero-Churn Performance Invariant (AXIOM-01 $\le 0.20\text{ ms}$ per segment, AXIOM-02 `0` heap bytes in `run()`).
    * **Law 7:** One Lead Timescale & Driver Hegemony (70/20/10 variance allocation, $\ge 85\%$ perceptual salience, $f \ge 0.30$ and $g \ge 0.65$).
    * **Law 8:** Monolithic Visual Simplicity & Immediate Legibility (Gestalt Common Fate, ban on multi-tier driver fragmentation, 5-to-10m 2-bar spectator test).
    * **Law 9:** Vibrant High-Luminance Color Aesthetics.
    * **Law 10:** Physical Spatial Invariance (AXIOM-03 bottom-to-top vertical invariant, `way == "DOWN"` bypass for `IS_GLOBAL = True`).
* **[NEW]** [`docs/research/2026-11-09_global_audio_modes_research_and_design.md`](../docs/research/2026-11-09_global_audio_modes_research_and_design.md):
  * Full forensic perceptual audit of the 5 earlier prototypes, the 4 Laws of Global Legibility, mathematical blueprints and verified reference skeletons for the 5 replacement Global Modes, and a 6-dimension evaluation rubric ($56.4\text{–}58.5 / 60$).
* **[MODIFY]** [`docs/contracts/README.md`](../docs/contracts/README.md) & [`docs/README.md`](../docs/README.md):
  * Indexed [`docs/contracts/global_mode_contract.md`](../docs/contracts/global_mode_contract.md) in the canonical Tier 1 documentation portal.

### 5 New Global Modes (`modes/` & `config/modes.json`)
* **[NEW]** [`modes/Monolithic_beat_blast_mode.py`](../modes/Monolithic_beat_blast_mode.py) (`"Monolithic Beat Blast"`, `LEAD = "beat"`, `SECONDARY = ("transient",)`):
  * Full-chandelier radial plasma detonation expanding from the architectural centroid `(0.620, 0.450)` across all 1,304 LEDs (`np.hypot(x_norm - 0.620, y_norm - 0.450)`), sampling `self.palette_lut` with white-hot transient crest flares (`self.white_flash`) on `drop_hit` and `is_real_beat`.
  * **Metrics:** `0.052 ms`, `0` heap bytes, `lead_share = 79.5%`, `sec_retained = 70.8%`.
* **[NEW]** [`modes/Architectural_vu_equalizer_mode.py`](../modes/Architectural_vu_equalizer_mode.py) (`"Architectural VU Equalizer"`, `LEAD = "level"`, `SECONDARY = ("spectrum",)`):
  * Unified vertical VU liquid column rising from floor (`altitude = 0.0`) to canopy (`altitude = 1.0`) across all pillars, bridges, and canopy with asymmetric attack/decay ballistics on `energy`, lateral meniscus tilt from `spectral_tilt`, and a high-saturation Amber/Gold (`#FF9900`–`#FFD700`) to Laser Red (`#FF0033`) gradient ($S = 1.0$).
  * **Metrics:** `0.0074 ms`, `0` heap bytes, `lead_share = 77.7%`, `sec_retained = 96.9%`.
* **[NEW]** [`modes/Concentric_radial_ripple_mode.py`](../modes/Concentric_radial_ripple_mode.py) (`"Concentric Radial Ripple"`, `LEAD = "beat"`, `SECONDARY = ("level",)`):
  * Emits 3 staggered concentric circular shockwave rings expanding outward from the chandelier centroid `(0.620, 0.450)` in Pure Ultraviolet (`#9D00FF`, $S = 1.0$), with metrical wave velocity coupled to `beat_phase` / `beat_pulse()` and `level` (`energy`) driving fallback drift and ring spawn amplitude.
  * **Metrics:** `0.025 ms`, `0` heap bytes, `lead_share = 71.6%`, `sec_retained = 99.6%`.
* **[NEW]** [`modes/Horizon_scanning_blade_mode.py`](../modes/Horizon_scanning_blade_mode.py) (`"Horizon Scanning Blade"`, `LEAD = "beat"`, `SECONDARY = ("transient",)`):
  * Sweeps a symmetric 180-degree twin-beam radar blade (`atan2(y_norm - 0.450, x_norm - 0.620)`) 360° around the chandelier in Emerald Neon (`#00FF88`) with a phosphor wake (`_wake`) and white-hot transient leading-edge flares (`tip_flare`) on `drop_hit` and `is_real_beat`.
  * **Metrics:** `0.022 ms`, `0` heap bytes, `lead_share = 94.1%`, `sec_retained = 73.0%`.
* **[NEW]** [`modes/Spectral_avalanche_mode.py`](../modes/Spectral_avalanche_mode.py) (`"Spectral Avalanche"`, `LEAD = "spectrum"`, `SECONDARY = ("beat",)`):
  * Top-to-bottom gravitational frequency waterfall along `altitude` driven by 16-band/8-band Mel spectral flux (`spec_flux`) and per-LED spectral altitude indexing (`z * 15.0`), colored via `self.palette_lut` with secondary `beat_pulse()` modulation.
  * **Metrics:** `0.025 ms`, `0` heap bytes, `lead_share = 96.0%`, `sec_retained = 100.1%`.
* **[MODIFY]** [`config/modes.json`](../config/modes.json) & [`hardware/VisualizerHud.py`](../hardware/VisualizerHud.py):
  * Mounted the 5 new Global Modes under `"global_modes"` in `config/modes.json` and updated the `VisualizerHud` fallback list and compacted `VisualizerHud.py` under the 500-line AXIOM-07 governance cap.

### Mood Sector, Desktop Show Control & Mode Studio Dependencies
* **[MODIFY]** [`mood/api.py`](../mood/api.py), [`mood/engine.py`](../mood/engine.py), [`mood/scene_policy.py`](../mood/scene_policy.py), [`mood/service.py`](../mood/service.py) & [`docs/contracts/mood_contract.md`](../docs/contracts/mood_contract.md):
  * Added per-scene dwell (`0.25s` on `DROP_IMPACT`, `2.0s` on `BUILDUP`, `3.5s` on `GROOVE`, `4.0s` on `CHILL`), per-scene crossfade durations (`0.8s`–`3.0s`), two-palette variant rotation per scene, and `DEFAULT_MANUAL_HOLD = 45.0s` manual override hold timer (`request_palette(..., hold=...)`).
* **[MODIFY]** [`core/Mode_master.py`](../core/Mode_master.py), [`core/TransitionBridge.py`](../core/TransitionBridge.py), [`core/CommandRouter.py`](../core/CommandRouter.py), [`hardware/Fake_leds.py`](../hardware/Fake_leds.py), [`hardware/Udp_Sender.py`](../hardware/Udp_Sender.py), [`hardware/Fake_ESP32.py`](../hardware/Fake_ESP32.py), [`hardware/VisualizerHud.py`](../hardware/VisualizerHud.py) & [`tools/mode_studio.py`](../tools/mode_studio.py):
  * Wired live Mood palette/auto-scene controls (`set_mood`, `set_mood_auto`, `[M]` / `[A]` hotkeys, 4 RGB swatches, crossfade progress) into both the `Fake_leds` Show Control panel and `tools/mode_studio.py` alongside the Global Mode scope (`G`) and `<` / `>` pickers.

### Test Suite Updates
* **[MODIFY]** [`tests/test_global_modes.py`](../tests/test_global_modes.py), [`tests/test_panel_show_control.py`](../tests/test_panel_show_control.py), [`tests/test_mood_sector.py`](../tests/test_mood_sector.py), [`tests/test_studio_mutes.py`](../tests/test_studio_mutes.py), [`tests/test_command_router.py`](../tests/test_command_router.py), [`tests/test_mode_master_snapshot.py`](../tests/test_mode_master_snapshot.py) & [`tests/test_fake_esp32_and_fake_leds.py`](../tests/test_fake_esp32_and_fake_leds.py):
  * Verified all 5 Global Modes across 2D spatial rendering, `bind_segment_geometry` rebinding, Law 5 dead-settings honesty, flywheel-lost resilience, Silence Law ballistic drain, AXIOM-01/02/07, Law 7 choreography dominance, Mood sector scene dwells/holds, and HUD/Studio controls.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/test_global_modes.py tests/test_panel_show_control.py tests/test_mode_helpers.py tests/governance/ -q`
  * **Result**: `106 passed, 66 subtests passed`
* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `600 passed, 5 deselected, 187 subtests passed`

---

## 4. Architecture Decisions & Trade-offs

* **Monolithic Single-Driver Metaphors over Multi-Role Splitting (Laws 1, 7, 8):** Every Global Mode evaluates a unified spatial metaphor across all 11 segments simultaneously via `SegmentSpatialProfile`, guaranteeing immediate spectator legibility from 5–10 meters within 2 musical bars.
* **Geometry Rebinding in `bind_segment_geometry` (Door 5 / Law 10):** Because `Segment.py` instantiates modes before calling `bind_segment_geometry(id, orientation, tags, coords_array)`, all 5 Global Modes recompute their pre-allocated spatial lookup vectors (`_radius`, `_angles`, `_color_gradient`, `_lut_indices`, `_band_indices_*`) in-place inside `bind_segment_geometry` so real chandelier coordinates are always active with zero runtime allocations in `run()`.

---

## 5. Open Items & Next Steps

* [ ] Live visual playtest of all 5 new Global Modes in the Pygame Simulator (`.\.venv\Scripts\python.exe Main.py --song --mode "Monolithic Beat Blast" --panel`).
