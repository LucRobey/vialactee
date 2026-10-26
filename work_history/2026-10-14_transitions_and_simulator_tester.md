# Work History: 1D Strip-Intrinsic Transitions, Chandelier Choreographies & Simulator Transition Tester

**Date:** 2026-10-14
**Scope:** `transitions/`, `hardware/Fake_leds.py`, `hardware/VisualizerHud.py`, `hardware/Fake_ESP32.py`, `hardware/Udp_Sender.py`, `core/Mode_master.py`, `tests/transitions/`, `docs/reference/transition_contract.md`

## 1. Context & Problem Statement
1. **2D Screen Assumption vs. 1D Sparse Chandelier:** Existing spatial wipes (`vertical_wipe`, `wipe_left_to_right`) normalized pixel coordinates across the global 2D room bounding box (`431 × 246`), causing horizontal rings ($y = \text{const}$) to flash simultaneously during vertical wipes and vertical pillars ($x = \text{const}$) to flash simultaneously during horizontal wipes.
2. **Midpoint Energy Loss:** Linear crossfades (`fade_in_out`) dip in perceived brightness at $p = 0.5$ due to LED gamma perception, and hard cuts lack organic or musical continuity.
3. **Interactive Transition Testing:** Waiting 20s for automatic timer transitions or structural cuts made it slow to preview specific transitions and durations in the simulator.

## 2. Solution & Architectural Changes

### A. 13 New Vectorized Transition Effects (`transitions/effects.py`, `transitions/engine.py`)
Implemented 4 new families of in-place NumPy transitions using pre-cached 1D strip coordinates (`_U_CACHE`) and deterministic spatial hashes (`_HASH_CACHE`):
- **Photonic & Organic Dissolves:**
  - `ember_dissolve`: Per-LED noise threshold takeover with a glowing gold/amber blackbody spark edge.
  - `luma_melt`: Luminance-keyed takeover where bright incoming pixels break through dark outgoing pixels first.
  - `breath_dip`: Parabolic brightness breath down to a 20% ambient floor (`0.20 + 0.80 * (2p - 1)^2`), swapping modes at the nadir ($p = 0.5$) and inhaling to full brightness.
- **1D Strip-Intrinsic Sweeps:**
  - `silk_wipe` / `silk_wipe_reverse`: Smoothstep wipe along normalized 1D strip index $u \in [0, 1]$ with a soft specular crest.
  - `iris_open` / `iris_close`: Symmetric center-out ($|u - 0.5| \times 2$) or edges-in aperture along each segment.
  - `zipper_merge`: Even LEDs sweep from $u=0 \to 1$ while odd LEDs sweep from $u=1 \to 0$, interlocking at $p = 0.5$.
- **Kinetic & Physics:**
  - `collider`: Twin cyan/magenta energy packets accelerate from both ends of each strip, collide at $u = 0.5$ ($p = 0.45$), and detonate outward to reveal the new mode.
  - `prism_sweep`: Chromatic dispersion wave with phase-shifted R, G, and B takeover fronts.
  - `flash_cut`: Instant mode swap at $p = 0.12$ masked by an exponential photographic flash decay.
- **Rhythmic & DJ Cuts:**
  - `staccato_shutter`: Accelerating square-wave gate (`cos(32 * pi * p^2)`) alternating between outgoing and incoming modes.
  - `transformer_cut`: Turntablist 3-chop stutter cut (`[0.12..0.22]`, `[0.35..0.48]`, `[0.60..0.78]`, full lock $\ge 0.85$).

### B. Physical Chandelier Stagger Choreographies (`transitions/stagger.py`)
- Added `ALTITUDE_CASCADE_DOWN` and `ALTITUDE_CASCADE_UP` grouping horizontal segments by true physical $Y$-altitude tiers (Canopy `h30/h00/h20` $\to$ Mid `h11/h32` $\to$ Low `h31/h10`).
- Added `BAY_WAVE_LR` and `BAY_WAVE_RL` sweeping across architectural bay columns (`h00` $\to$ `v1` $\to$ `h10/h11` $\to$ `v2` $\to$ `h20` $\to$ `v3` $\to$ `h30..32` $\to$ `v4`).

### C. Simulator Transition Tester UI (`hardware/VisualizerHud.py`, `hardware/Fake_leds.py`, `hardware/Udp_Sender.py`, `hardware/Fake_ESP32.py`)
- Extracted HUD rendering into `hardware/VisualizerHud.py` to keep `hardware/Fake_leds.py` at 292 lines (strictly below the 500-line AXIOM-07 limit).
- Added the interactive **TRANSITION TESTER** panel on the simulator window:
  - Transition selector (`<` / `>` buttons or `[` / `]` keys) cycling through `"AUTO"` and all 23 transitions in `AVAILABLE_TRANSITIONS`.
  - Duration selector (`-0.5`, `-0.1`, `+0.1`, `+0.5` buttons or `-` / `=` keys) for transition duration $N$ seconds (default `1.2s`).
  - `SEND REQUEST (Hotkey: T)` button that dispatches `request_next(technique=..., duration=N)` over localhost UDP (`CONTROL_PORT = 9004`) to `Udp_Sender` / `Mode_master`, which beat-quantizes the launch within the 1.2s beat window (`_downbeat_timeout = 1.20`s).
  - Live status & progress bar (`READY`, `QUEUED: waiting for beat (<= 1.2s)...`, `ACTIVE: <technique> (<pct>%)`), plus a clean `SEGMENT MODES` table on the left of the simulator window.

### D. Multi-Family Transition Contract System (`transitions/families.py`, `transitions/manager.py`, `transitions/effects.py`, `transitions/engine.py`)
- Defined 8 abstract `TransitionFamily` contracts (`ROOM_EPI_2D`, `ROOM_SWEEP_2D`, `STRIP_SWEEP_1D`, `STRIP_FOCAL_1D`, `STAGGERABLE`, `STOCHASTIC_ORGANIC`, `RHYTHMIC_CHOP`, `MODE_COOPERATIVE`) where each transition belongs to a `frozenset` of families.
- `roll_transition_params(technique)` rolls fresh generative parameters on every transition trigger (architectural 2D `(epicenter_x, epicenter_y)` and `spiral_sign` for `ROOM_EPI_2D`, 1D `focal_u` for `STRIP_FOCAL_1D`, `edge_width` for `STRIP_SWEEP_1D`, spatial noise `seed` and `spark_intensity` for `STOCHASTIC_ORGANIC`, and `chop_count`/`flash_decay` for `RHYTHMIC_CHOP`) so triggering the same transition twice produces a unique visual event.
- `is_staggerable(technique)` and `get_allowed_stagger_patterns(technique)` enforce physical chandelier constraints (2D room-epicenter transitions like `explosion`, `spiral`, `box_wipe` always run `SIMULTANEOUS`).

### E. 3-Layer Mode-Cooperative Handshake (`core/Segment.py`, `core/TransitionBridge.py`, `modes/Mode.py`, and Mode Subclasses)
- `Segment.change_mode` zeroes `dual_rgb_list` on transition start (eliminating stale buffer ghosting), `Segment.update` drives `activ_mode_obj.on_transition_exit(prog)` and `target_mode.on_transition_enter(prog)` prior to rendering when `mode_handshake=True`, and `Segment._complete_transition` copies `dual_rgb_list` into `rgb_list` so stateful trails survive handoff.
- `Mode` exposes `_exit_progress`, `_enter_progress`, `transition_scale`, and accelerated exit trail decay in `fade_to_black` / `fade_to_black_segment_vectorized`.
- Wired physical exit wind-down and enter bloom-in into `Plasma_fire_mode`, `Power_bar_mode`, `Middle_bar_mode`, `Matrix_rain_mode`, `Extending_waves_mode`, `Shining_stars_mode`, `Flying_ball_mode`, and `Magnetic_ball_mode`.

## 3. Verification
- Executed `python -m pytest tests/transitions/ tests/governance/ tests/test_all_modes_musical_context.py -q`.

