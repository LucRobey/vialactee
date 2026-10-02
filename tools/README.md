# Vialactée Developer Tools

This directory contains developer utilities, standalone visualizer studios, and testing harnesses.

---

## 🎨 `mode_studio.py` — Visual Mode Authoring & Test Studio

A standalone developer visualizer that runs **100% bit-for-bit identical audio analysis** to the physical chandelier hardware, while letting you author, preview, and hot-reload modes in real time.

```bash
# Basic launch (defaults to Palladium.mp3, MultiBandOnsetAudioAnalyzer, and Static_wave_mode with 80 LEDs)
python tools/mode_studio.py

# Launch with a specific song and mode
python tools/mode_studio.py --song assets/musics/mp3_files/Nightcall.mp3 --mode Bary_rainbow_mode

# Compare against the legacy single-ODF baseline
python tools/mode_studio.py --model AudioAnalyzer

# Launch with custom LED length
python tools/mode_studio.py --leds 120
```

### Key Capabilities

1. **Hardware-Parity Music Analyzer:**
   - Instantiates the exact production [`Listener`](../core/Listener.py), [`MultiBandOnsetAudioAnalyzer`](../core/MultiBandOnsetAudioAnalyzer.py) (default), and [`AudioIngestion`](../core/AudioIngestion.py) classes. Supports `--model AudioAnalyzer` for legacy comparisons.
   - Zero mocks or approximations: runs the real 32-band onset derivative streams, kick anti-phase disambiguation, dense Pearson template bank, and phase back-projection.
   - Slices audio chunks at 44.1 kHz with a 5.0-second lookahead pre-roll so audio heard in your headphones/speakers aligns to the millisecond with the visual downbeats.

2. **Instant Hot-Reload (`[R]` Key):**
   - Edit any mode in `modes/` (e.g. `modes/Static_wave_mode.py`) in VS Code.
   - Hit **`[R]`** in the Pygame window.
   - Python reloads the module via `importlib.reload()` and continues playback immediately without restarting the song or resetting the beat tracker.

3. **Live 5-Card Telemetry & Context HUD:**
   - **Card 0 (Flywheel & BPM):** Circular phase dial showing real-time `beat_phase` ($0.0 \to 1.0$), base tempo, lock status, Pearson confidence meter, and total beats.
   - **Card 1 (Musical Regime Engine & 2x2 State Matrix):** Real-time canonical regime badge (`DEEP_AMBIENT`, `FLOATING_PULSE`, `THE_POCKET`, `CHAOTIC_FILL`, `PRE_DROP_BUILDUP`, `STRUCTURAL_CHANGE`), transition crossfade progress bar (`regime_blend`), dwell time with stability lock, pre-drop countdown alerts, and embedded **2x2 Regime State Matrix ($T \times S$ Phase Plane Mini-Grid)** showing real-time $(T, S)$ navigation, Schmitt hysteresis deadbands, and active quadrant highlights.
   - **Card 2 (Salience & Trust Telemetry):** Rhythmic Salience ($S$) with dynamic Schmitt deadband shaded, Beat Trust ($T$) with dynamic Schmitt deadband shaded, Salience Gradient ($\Delta R$) bipolar gauge with pre-drop buildup trigger tick, and Telemetry Dynamics Summary box tracking speaker vs lookahead lead deltas and lock coupling states.
   - **Card 3 (Beat & Transient Tagging):** Flashing badges for `● REAL BEAT` vs `◐ DROPPED / BREAKDOWN`, plus `[Bass/Kick]`, `[Snare/Mid]`, `[Hi-hat/Cymbal]` tags, and mode authoring guidelines.
   - **Card 4 (Spectral Dynamics & Harmony):** N-Band Mel filterbank dynamics, total asserved power meter, and 12-tone chromagram dominant key class.
   - **Scrubber Readout:** Interactive progress bar blits live values for `Trust (T)` (Speaker & Live), `Salience (S)` (Speaker & Live), `ΔR`, `[Regime Badge]`, and flashing `[⚠️ DROP IN X.Xs!]` alerts.

### Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| **`[R]`** | **Hot-Reload** active mode code from disk |
| **`[Space]`** | Pause / Resume playback and animation |
| **`[↑] / [↓]`** | Cycle through all 23 modes in `modes/` |
| **`[←] / [→]`** | Seek -5s / +5s backward / forward |
| **`[N] / [P]`** | Next / Previous song in playlist |
| **`[1] - [9]`** | Jump directly to track 1 through 9 |
| **`[+] / [-]`** | Increase / decrease audio sensitivity |
| **`[O]`** | Toggle between Horizontal and Vertical strip preview |
| **`[K] / [L]`** | Calibrate A/V sync offset (-10ms / +10ms) |
| **`[\]`** | Reset A/V sync offset to 0ms |
| **Click on scrubber** | Seek to exact timestamp |
| **`[Esc]`** | Exit Mode Studio |

---

## 🔬 `music_studio.py` — Real-Time DSP & Music Analysis Laboratory

A standalone interactive laboratory dedicated to **inspecting, testing, evaluating, and fine-tuning the music analysis algorithms themselves** with bit-for-bit hardware parity.

```bash
# Basic launch (defaults to Palladium.mp3 with 80 reference LEDs, MultiBandOnsetAudioAnalyzer)
python tools/music_studio.py

# Launch with a specific track
python tools/music_studio.py --song assets/musics/mp3_files/Nightcall.mp3

# Launch with a specific model for algorithm research/comparison
python tools/music_studio.py --model MultiBandOnsetAudioAnalyzer
python tools/music_studio.py --model AudioAnalyzer
```

### Deep Analysis Instruments & Panels

1. **5.0-Second Lookahead ODF Oscilloscope:**
   - Visualizes the past 1.0s and next 4.0s of multi-band positive spectral flux streaming toward the speaker line.
   - Distinct **`▼ SPEAKER NOW`** line marking exact acoustic speaker emission with hardware DAC compensation.
   - Overlays the **Oracle Template Pulse Wave** showing anticipated beat peaks before they hit the speakers.
   - Highlights the pre-drop buildup anticipation zone with countdown label when $\Delta R \ge +0.40$.
   - Real-time sub-header readouts comparing Speaker vs Lookahead (+5.0s) Salience and Beat Trust.

2. **Anticipation Flywheel & Dual Beat Trust Core:**
   - **Continuous Phase Dial:** 360-degree mechanical flywheel needle tracking `beat_phase` ($0.0 \to 1.0$).
   - **Speaker Beat Trust ($T$):** Meter with Schmitt trigger deadband $[0.35, 0.50]$ shaded and `[TRUSTED / COASTING / DRIFTING]` states.
   - **Lookahead Beat Trust ($T_{\text{live}}$) & Pearson $r$:** Predictive flywheel stability meter.
   - **High-Impact Beat Flash:** Flashes on downbeats with frequency classification:
     - 🔴 **Bass/Kick** (< 150 Hz)
     - 🟢 **Snare/Mid** (150 - 2000 Hz)
     - 🔵 **Hi-hat/Cymbal** (> 2000 Hz)
   - Badge classifying `● REAL ACOUSTIC BEAT` vs `◐ DROPPED / BREAKDOWN BEAT`.
   - Logarithmic base-tempo class $\log_2(\text{BPM}/60) \pmod 1$ and harmonic candidate readouts.

3. **8-Band Frequency Dynamics & Spectral Peaks:**
   - 8 Mel filterbank columns (Sub-bass through Air).
   - Triple-layer display: Raw energy (dark ghost bar), ADSR-smoothed energy (solid color bar), and Asserved peak cap ($0.0 \to 1.0$).
   - Red LED peak indicators triggering on transient spikes.
   - Total Power Asservation meter (Local Max & Global Max envelopes).

4. **12-Tone Chromagram & Harmony Analyzer:**
   - 12 pitch classes ($C, C\sharp, D, \dots, B$).
   - Visual bar heights and dominant key/chord badge.

5. **Structural Novelty & Regime State Engine (Panel 5):**
   - Header with Canonical Musical Regime badge (`[● THE_POCKET]`, `[▲ PRE_DROP_BUILDUP]`, etc.) and flashing `⚠️ DROP COUNTDOWN: X.XXs` alert.
   - Rolling real-time graph plotting Combined Novelty (Cyan), Local Max LM (Orange), and Global Max GM (Purple).
   - Expanded right-sidebar instrumentation:
     - **Asserved Novelty Meter:** Gauge ($0.0 \to 1.0$) with song drop threshold line.
     - **Memory Envelopes:** STM Power, LTM Power, Novelty LM, Novelty GM, and silence frame counters.
     - **Rhythmic Salience ($S$) Meter:** Speaker vs Live (+5s) readouts with Schmitt trigger deadband $[0.35, 0.45]$ shaded and `[POCKET / AMBIENT / HYST]` badges.
     - **Salience Gradient ($\Delta R$) Gauge:** Bipolar $[-0.5, +0.5]$ meter with center tick, $+0.40$ buildup threshold line, and trigger alert.
     - **Semantic Context Flags:** Mini-card reporting `RHYTHMIC`, `IN POCKET`, `BUILDUP`, and `STRUCT CUT`.
     - **Regime Transition Crossfade:** Blend progress bar ($0.0 \to 1.0$), source regime readout, and dwell time with stability lock indicator.
     - **2x2 Regime State Matrix ($T \times S$) Phase Plane Mini-Grid:** Visualizes musical navigation across $(T, S)$ state plane (`CHAOTIC_FILL`, `THE_POCKET`, `DEEP_AMBIENT`, `FLOATING_PULSE`), with active quadrant highlights, Schmitt hysteresis zones, crosshairs, coordinate readouts, and override alert banners.

6. **Interactive Live Parameter Tuning Drawer (`[T]` Key):**
   - Press **`[T]`** to slide open the live parameter editor (dynamically sized, zero-overflow backdrop).
   - Select parameter with **`[↑] / [↓]`**, adjust with **`[←] / [→]`**, or **click / drag with mouse**:
     - `sensi` (Audio Sensitivity)
     - `moderate_confidence_threshold` (Flywheel lock sensitivity)
     - `high_confidence_threshold` (Flywheel high snap threshold)
     - `strong_peak_multiplier` (Peak onset sensitivity)
     - `real_beat_baseline_ratio` (Drum presence validation)
     - `song_novelty_asserved_th` (Verse/Chorus drop threshold)
     - `silence_power_threshold` (Silence detection floor)
     - `drop_buildup` (Pre-drop buildup salience gradient threshold)
     - `salience_low` (Rhythmic salience Schmitt low threshold)
     - `salience_high` (Rhythmic salience Schmitt high threshold)
     - `trust_low` (Beat trust Schmitt low threshold)
     - `trust_high` (Beat trust Schmitt high threshold)
   - Real-time deadband inversion guard prevents hysteresis collapse.
   - Panel 5 phase plane matrix and meters dynamically track live threshold adjustments.
   - Click directly on any parameter row to select it; click or drag along any slider bar to set values.
   - Press **`[D]`** inside drawer to reset DSP and Context parameters to defaults.

7. **Miniature Chandelier Preview:**
   - 80-pixel virtual LED strip across the top header displaying real-time chandelier response.

### Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| **`[Space]`** | Pause / Resume playback and analysis |
| **`[←] / [→]`** | Seek -5s / +5s backward / forward |
| **`[N] / [P]`** | Next / Previous track in playlist |
| **`[1] - [9]`** | Jump directly to track 1 through 9 |
| **`[K] / [L]`** | Calibrate A/V sync offset (-10ms / +10ms) |
| **`[\]`** | Reset A/V sync offset to 0ms |
| **`[T]`** | Toggle Live Parameter Tuning Drawer |
| **`[↑] / [↓]`** | Select parameter in Tuning Drawer |
| **`[←] / [→]`** | Adjust selected parameter value |
| **`Mouse Click / Drag`** | Click parameter row to select; drag slider bar to tune |
| **`[D]`** | Reset DSP parameters to defaults |
| **`[+] / [-]`** | Increase / decrease audio sensitivity |
| **Click scrubber** | Seek to exact song timestamp |
| **`[Esc]`** | Exit Music Studio |

