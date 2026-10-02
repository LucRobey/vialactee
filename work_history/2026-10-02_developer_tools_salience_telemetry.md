# [2026-10-02] Developer Tools Upgrade: Real-Time Salience & Context Telemetry

> **Date:** 2026-10-02  
> **Session ID:** `d82e7d9c-3587-45a1-b4ea-4c6eac1dd0c1`  
> **Agent / Model:** Antigravity (Gemini 3.8 Flash High)  
> **Primary Goal:** Upgrade developer visualizers (`tools/mode_studio.py` and `tools/music_studio.py`) to display real-time DSP telemetry, canonical musical regimes, salience/trust gauges, countdown alerts, and 2x2 state matrix navigation with zero heap allocation at 60 FPS.  
> **Status:** COMPLETED  

---

## 1. Context & Motivation

Following the implementation of `core/MusicalContextEngine.py`, `rhythm_salience`, `beat_trust`, and lookahead anticipation (`salience_gradient` $\Delta R \ge +0.40$), the developer visualizer tools (`tools/mode_studio.py` and `tools/music_studio.py`) required direct visualization and interactive inspection capabilities:

1. **Mode Authoring Visibility:** Mode authors in `mode_studio.py` needed real-time readouts of canonical regimes (`THE_POCKET`, `DEEP_AMBIENT`, etc.), transition crossfade progress (`regime_blend`), Schmitt trigger hysteresis states, and incoming drop alerts while hot-reloading modes with `[R]`.
2. **DSP Laboratory Instruments:** Algorithm designers in `music_studio.py` needed high-fidelity visual instruments comparing speaker-delayed vs lookahead signals, live tuning of context thresholds (`drop_buildup`, `salience_high`, `trust_high`), and a 2x2 phase plane grid ($T \times S$) tracking state navigation across the 4 steady-state regimes.
3. **Zero-Allocation 60 FPS Performance:** All new UI widgets, meters, gauges, and text rendering must adhere strictly to zero heap allocations in hot draw paths using the `_text_cache` system.

---

## 2. Changes Made

### 1. `tools/mode_studio.py` — Mode Authoring & Test Studio
* **Window Dimensions:** Expanded to 1380x760 to accommodate 5 dedicated telemetry cards.
* **Palette & Icons:** Added `REGIME_COLORS`, `REGIME_BG_COLORS`, and `REGIME_ICONS` matching the 6 canonical regimes.
* **Header Scrubber Telemetry:** Added live readouts on the timeline scrubber:
  - `Trust (T)` with color coding (`TRUSTED`, `COASTING`, `DRIFTING`).
  - `Salience (S)` with color coding (`POCKET`, `AMBIENT`, `HYSTERESIS`).
  - `Salience Gradient (ΔR)`.
  - Canonical Musical Regime Badge (`[● THE_POCKET]`, etc.).
  - Flashing pre-drop alert: `[⚠️ DROP IN X.Xs!]`.
* **5 Dedicated Telemetry Cards (`_draw_telemetry_hud`):**
  - **Card 0 (`_draw_flywheel_card`):** Phase dial, BPM, Flywheel Status, Pearson confidence meter, total beats, and octave class.
  - **Card 1 (`_draw_context_card`):** Canonical regime badge with pulse glow on buildup, transition crossfade progress bar (`regime_blend`), previous regime readout, dwell time lock indicator (`🔒 LOCKED` vs `✓ STEADY`), and pre-drop countdown / semantic context flags.
  - **Card 2 (`_draw_salience_trust_card`):**
    - Rhythmic Salience ($S$) meter with shaded Schmitt deadband $[0.35, 0.45]$ and ticks at 35% and 45%.
    - Beat Trust ($T$) meter with shaded Schmitt deadband $[0.35, 0.50]$ and ticks at 35% and 50%.
    - Salience Gradient ($\Delta R$) bipolar gauge $[-0.5, +0.5]$ with center tick and $+0.40$ buildup trigger line.
  - **Card 3 (`_draw_beat_card`):** Real vs Dropped beat tags, frequency band classification (`Bass/Kick`, `Snare/Mid`, `Hi-hat/Cymbal`), and mode authoring recipes.
  - **Card 4 (`_draw_spectral_card`):** N-Band Mel filterbank dynamics, total asserved power meter, and 12-tone chromagram dominant key class.

### 2. `tools/music_studio.py` — Real-Time DSP Laboratory
* **Window Dimensions:** Standardized to 1440x960.
* **Header Scrubber Telemetry:** Added real-time readouts for `Trust (T)`, `Salience (S)`, `ΔR`, canonical regime badge, and incoming drop countdown.
* **Panel 1 (`_draw_panel_1_lookahead_oscilloscope`):**
  - Added sub-header readouts comparing Speaker vs Lookahead (+5.0s) Salience and Beat Trust.
  - Added highlighted pre-drop anticipation overlay zone with countdown label when $\Delta R \ge +0.40$.
* **Panel 2 (`_draw_panel_2_flywheel_and_beats`):**
  - Upgraded with dual meters: Speaker Beat Trust ($T$) with Schmitt deadband $[0.35, 0.50]$ and Lookahead Beat Trust ($T_{\text{live}}$) & Pearson $r$.
* **Panel 5 (`_draw_panel_5_structural_novelty`):**
  - Expanded height to 320 px to seamlessly fill available vertical space.
  - Header displays Canonical Musical Regime badge and flashing `⚠️ DROP COUNTDOWN: X.XXs` alert alongside Verse/Chorus and Song Transition badges.
  - Subdivided right sidebar into two parallel instrument columns:
    - **Column 1:** Asserved Novelty gauge + drop threshold tick, memory envelopes (STM/LTM Power, Novelty LM/GM, silence frames), Rhythmic Salience ($S$) meter with Schmitt deadband $[0.35, 0.45]$, Salience Gradient ($\Delta R$) bipolar gauge with $+0.40$ threshold tick, and Semantic Context Flags card (`RHYTHMIC`, `IN POCKET`, `BUILDUP`, `STRUCT CUT`).
    - **Column 2:** Canonical Regime Badge, dwell time with lock status, transition crossfade progress bar (`regime_blend`), and the **2x2 Regime State Matrix ($T \times S$) Phase Plane Mini-Grid**:
      - 4 quadrants: `CHAOTIC_FILL`, `THE_POCKET`, `DEEP_AMBIENT`, `FLOATING_PULSE`.
      - Active quadrant background glow.
      - Shaded Schmitt hysteresis deadbands ($T \in [0.35, 0.50]$, $S \in [0.35, 0.45]$) with `HYST` label.
      - Crosshair guides and glowing current $(T, S)$ navigation point with coordinate readout.
      - Override alert banners for `PRE_DROP_BUILDUP` and `STRUCTURAL_CHANGE`.
* **Panel 6 (Tuning Drawer):** Added live sliders for `drop_buildup`, `salience_high`, and `trust_high`, and wired reset on `[D]`.

### 3. Documentation
* **`tools/README.md`**: Updated to comprehensively describe the new 5-card HUD in `mode_studio.py` and the upgraded panels, telemetry gauges, and 2x2 state matrix in `music_studio.py`.

---

## 3. Verification & Testing

* **`scratch/test_music_studio_verification.py`**:
  - Model loader (AudioAnalyzer and MultiBandOnsetAudioAnalyzer): **PASS**
  - Sample-accurate audio feeder & 5.0s lookahead oscilloscope index alignment (index 59 = Speaker NOW): **PASS**
  - Macro novelty time synchronization: **PASS**
  - Headless Pygame rendering across all panels including updated Panel 5: **PASS** (113 cache entries, 0 errors).
* **`scratch/test_mode_studio_verification.py`**:
  - Model loader: **PASS**
  - Sample-accurate feeder and accumulator: **PASS**
  - Headless GUI rendering across all 5 telemetry cards: **PASS** (66 cache entries, 0 errors).
  - Beat confidence across LOW, MODERATE, HIGH tiers: **PASS**.
* **Full Pytest Suite (`python -m pytest`)**:
  - **147 passed, 5 deselected** in 21.69s.
  - Zero regressions across governance, listener, mode rendering, audio presets, and musical context engine tests.

---

## 4. Second-Pass Adversarial Audit & Fixes

During rigorous secondary adversarial review, several subtle functional bugs, visual layout regressions, and architecture gaps were discovered in the prior implementation and resolved:

1. **Tuning Drawer Geometry Overflow (`music_studio.py`):**
   - *Problem:* `dh` was hardcoded to 420 px. When 3 new context parameters were added, items 7 (`drop_buildup`), 8 (`salience_high`), and 9 (`trust_high`) extended down to y = 642 px, overflowing past the drawer's bottom border (y = 540 px) by 102 px.
   - *Fix:* Re-architected drawer geometry to calculate `dh = 66 + len(self.tuning_params) * item_step + 14` and `dy = max(40, (self.height - 35 - dh) // 2)`. All 12 parameters now fit strictly inside the backdrop and gold border with zero overflow.

2. **Hysteresis Deadband Inversion Guard (`music_studio.py`):**
   - *Problem:* If `salience_high` or `trust_high` was tuned below `salience_low` or `trust_low`, the Schmitt trigger hysteresis collapsed, resulting in frame-by-frame state flapping when signal amplitude was between thresholds.
   - *Fix:* Added `salience_low` and `trust_low` to `tuning_params`, and implemented dynamic clamping in `_adjust_param()` enforcing a minimum deadband gap $\ge 0.02$.

3. **Dynamic Threshold Synchronization:**
   - *Problem:* Panel 2 and Panel 5 in `music_studio.py`, as well as Card 2 in `mode_studio.py`, hardcoded Schmitt deadband borders to `0.35`, `0.45`, and `0.50`, ignoring slider tuning adjustments.
   - *Fix:* Dynamically query `context.salience_low`, `context.salience_high`, `context.trust_low`, `context.trust_high`, and `context.drop_buildup_threshold` to render meter tick marks, shaded deadband zones, and 2x2 grid lines.

4. **Regime State Desynchronization on Seek & Track Switch:**
   - *Problem:* `seek()` and `change_song()` in both studios called `listener.analyzer.reset()`, leaving `MusicalContextEngine` with stale regime dwell times, countdowns, and buildup cooldowns.
   - *Fix:* Updated `seek()` and `change_song()` in both tools to invoke `listener.reset()`, resetting the analyzer, ring buffers, and context engine synchronously.

5. **2x2 State Matrix Phase Plane in `mode_studio.py`:**
   - *Problem:* Mode authors lacked visual orientation on the $(T, S)$ state plane, and Card 1 had 130 px of unused empty space.
   - *Fix:* Embedded the 2x2 Regime State Matrix ($T \times S$ Phase Plane Mini-Grid) into Card 1, providing mode authors with quadrant tracking, Schmitt hysteresis bands, crosshairs, coordinate readouts, and override alerts.

6. **Dead Code Elimination (`mode_studio.py`):**
   - *Problem:* Lines 1376-1505 contained obsolete orphan methods `_draw_fft_card()` and `_draw_chroma_card()`.
   - *Fix:* Completely removed all dead methods.

* **Audit Verification Record:**
  - `scratch/test_drawer_and_resets.py`: **4/4 PASSED** (Drawer bounds, context reset on seek, deadband inversion guard, mode studio 2x2 matrix render).
  - Full pytest suite (`python -m pytest`): **147 passed, 5 deselected** in 21.69s.
