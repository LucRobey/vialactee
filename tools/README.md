# Vialactée Developer Tools

This directory contains developer utilities, standalone visualizer studios, and testing harnesses.

---

## 🎨 `mode_studio.py` — Visual Mode Authoring & Test Studio

A standalone developer visualizer that runs **100% bit-for-bit identical audio analysis** to the physical chandelier hardware, while letting you author, preview, and hot-reload modes in real time.

```bash
# Basic launch (defaults to Palladium.mp3 and Static_wave_mode with 80 LEDs)
python tools/mode_studio.py

# Launch with a specific song and mode
python tools/mode_studio.py --song assets/musics/mp3_files/Nightcall.mp3 --mode Bary_rainbow_mode

# Launch with custom LED length
python tools/mode_studio.py --leds 120
```

### Key Capabilities

1. **Hardware-Parity Music Analyzer:**
   - Instantiates the exact production [`Listener`](../core/Listener.py), [`AudioAnalyzer`](../core/AudioAnalyzer.py) (Anticipation Flywheel "Oracle"), and [`AudioIngestion`](../core/AudioIngestion.py) classes.
   - Zero mocks or approximations: runs the real $O(1)$ Pearson template bank, logarithmic tempo classes, and phase back-projection.
   - Slices audio chunks at 44.1 kHz with a 5.0-second lookahead pre-roll so audio heard in your headphones/speakers aligns to the millisecond with the visual downbeats.

2. **Instant Hot-Reload (`[R]` Key):**
   - Edit any mode in `modes/` (e.g. `modes/Static_wave_mode.py`) in VS Code.
   - Hit **`[R]`** in the Pygame window.
   - Python reloads the module via `importlib.reload()` and continues playback immediately without restarting the song or resetting the beat tracker.

3. **Live Oracle Telemetry HUD:**
   - **Continuous Flywheel:** Circular dial showing real-time `beat_phase` ($0.0 \to 1.0$), BPM, and lock confidence.
   - **Beat Classification:** Flashing badges for `● REAL BEAT` vs `◐ DROPPED / BREAKDOWN`, plus `[Bass/Kick]`, `[Snare/Mid]`, `[Hi-hat/Cymbal]` tags.
   - **8-Band Equalizer:** Live auto-gain normalized frequency bands.
   - **12-Tone Chromagram:** Real-time musical pitch classes and dominant chord key.
   - **Structure Detector:** Indicators for `is_verse_chorus_change` (drop detection) and `is_song_change`.

### Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| **`[R]`** | **Hot-Reload** active mode code from disk |
| **`[Space]`** | Pause / Resume playback and animation |
| **`[↑] / [↓]`** | Cycle through all 20 modes in `modes/` |
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
# Basic launch (defaults to Palladium.mp3 with 80 reference LEDs)
python tools/music_studio.py

# Launch with a specific track
python tools/music_studio.py --song assets/musics/mp3_files/Nightcall.mp3
```

### Deep Analysis Instruments & Panels

1. **5.0-Second Lookahead ODF Oscilloscope:**
   - Visualizes the past 1.0s and next 4.0s of multi-band positive spectral flux streaming toward the speaker line.
   - Distinct **`▼ SPEAKER NOW`** line marking exact acoustic speaker emission with hardware DAC compensation.
   - Overlays the **Oracle Template Pulse Wave** showing anticipated beat peaks before they hit the speakers.
   - Reference threshold lines for rolling flux baseline and strong peak multipliers.

2. **Anticipation Flywheel & Beat Tracker Core:**
   - **Continuous Phase Dial:** 360-degree mechanical flywheel needle tracking `beat_phase` ($0.0 \to 1.0$).
   - **Lock / Coasting Ring:** Glowing Emerald Green when `LOCKED` ($\ge 15\%$ Pearson confidence) and Amber/Orange when `COASTING` through drum breakdowns.
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

5. **Structural Novelty, Tension & Drop Detection Scope:**
   - Rolling real-time graph plotting:
     - **Combined Novelty** (Cyan): Instantaneous STM vs LTM timbral divergence + power difference.
     - **Local Max (LM)** (Orange): Fast decay envelope.
     - **Global Max (GM)** (Purple): Macro-structure tension envelope.
   - Asserved Novelty gauge ($0.0 \to 1.0$) with song drop threshold line.
   - Flashing badges for `★ VERSE / CHORUS DROP` and `⚡ SONG TRANSITION`.

6. **Interactive Live Parameter Tuning Drawer (`[T]` Key):**
   - Press **`[T]`** to slide open the live parameter editor.
   - Select parameter with **`[↑] / [↓]`**, adjust with **`[←] / [→]`**:
     - `sensi` (Audio Sensitivity)
     - `moderate_confidence_threshold` (Flywheel lock sensitivity)
     - `high_confidence_threshold` (Flywheel high snap threshold)
     - `strong_peak_multiplier` (Peak onset sensitivity)
     - `real_beat_baseline_ratio` (Drum presence validation)
     - `song_novelty_asserved_th` (Verse/Chorus drop threshold)
     - `silence_power_threshold` (Silence detection floor)
   - Press **`[D]`** inside drawer to reset parameters to default `RhythmConfig`.

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
| **`[D]`** | Reset DSP parameters to defaults |
| **`[+] / [-]`** | Increase / decrease audio sensitivity |
| **Click scrubber** | Seek to exact song timestamp |
| **`[Esc]`** | Exit Music Studio |

