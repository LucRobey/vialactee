# Developer Tools & Offline Studios Guide

> **Location:** `docs/manuals/developer_tools.md` (Tier 2 Operational Manual)  
> **Source Directory:** [`tools/`](../../tools/), [`hardware/Fake_leds.py`](../../hardware/Fake_leds.py), [`research/benchmarks/`](../../research/benchmarks/)  
> **Target Audience:** Developers, DSP Researchers, and Visual Mode Designers

This manual covers the offline graphical workbenches, interactive studios, and simulation tools available in Vialactée.

---

## 1. The Pygame Visualizer (`Fake_leds.py`)

When running `Main.py` on a PC (`"HARDWARE_MODE": "simulation"` or `"auto"`), the system spawns `hardware/Fake_ESP32.py`, which renders into `hardware/Fake_leds.py`.
- **Dynamic Topology:** Automatically scales and renders all active chandelier segments according to `config/segments_*.json`.
- **Audio HUD:** When `"show_music_analyser_panel": true`, overlays real-time FFT bands, spectral flux, instant volume, BPM estimates, and flywheel beat indicators on top of the chandelier display.

---

## 2. Mode Studio (`tools/mode_studio.py`)

A standalone visual mode development and testing workbench that renders a single LED strip alongside a live audio telemetry HUD and interactive parameter sliders — without launching the full multi-segment simulator or web interface.

### 2.1 Usage & CLI Flags

```bash
# Launch with default settings (first mode in modes.json, default song)
python tools/mode_studio.py

# Launch directly into a specific mode with a specific song
python tools/mode_studio.py --mode "Beat Runner" --song "stromae"

# Launch with live microphone capture instead of an audio file
python tools/mode_studio.py --mode "Impact Shockwave" --mic

# Test vertical strip behavior with custom LED count
python tools/mode_studio.py --mode "Plasma Fire" --leds 150 --orientation vertical

# List all registered modes in config/modes.json
python tools/mode_studio.py --list
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--mode`, `-m` | First mode | Initial mode name or substring (case-insensitive, e.g. `"beat"`, `"shockwave"`). |
| `--song`, `-s` | First `.mp3` | Song name or substring from `songs/`, or path to an audio file. |
| `--mic` | `False` | Use live microphone input (`Local_Microphone`) instead of an audio file. |
| `--leds`, `-n` | `150` | Number of simulated LEDs on the strip (`16..600`). |
| `--orientation` | `horizontal` | Strip orientation: `horizontal` or `vertical`. |
| `--fps` | `60` | Target render frame rate (`15..120`), for profiling against AXIOM-01 ($\le 20.0\text{ ms}$). |
| `--list` | — | Print all available modes from `config/modes.json` and exit. |

### 2.2 HUD Layout & Keyboard Shortcuts

- **Top Toolbar:** Mode selector (`◀` / `▶`), Song selector (`◀` / `▶`), Orientation toggle (`HORIZ` / `VERT`), Direction toggle (`DOWN` / `UP`), and LED count controls (`-25` / `+25`).
- **Center Canvas:** Large LED strip viewport with pixel glow halos, LED index ruler (`0`, `N/4`, `N/2`, `3N/4`, `N-1`), and center crosshair.
- **Bottom Telemetry Cards:**
  1. **8-Band Mel Spectrum (`asserved_fft_band`)** + `band_flux` peak indicators.
  2. **Rhythm & Flywheel Card:** Live BPM, `beat_phase` progress bar, `beat_confidence`, and `is_real_beat` / `is_dropped_beat` / `is_song_change` badges.
  3. **Live Mode Settings Card:** Interactive sliders, toggles, and dropdowns auto-generated from `mode.get_settings_schema()` with a `Reset Defaults` button.

| Key | Action |
| :--- | :--- |
| `←` / `→` | Previous / Next Mode |
| `[` / `]` | Previous / Next Song |
| `SPACE` | Manual Beat Trigger (`is_beat = True`, `is_real_beat = True`) |
| `G` | Ghost / Coasting Beat Trigger (`is_beat = True`, `is_real_beat = False`) |
| `D` | Toggle strip direction (`DOWN` $\leftrightarrow$ `UP`) |
| `O` | Toggle strip orientation (`horizontal` $\leftrightarrow$ `vertical`) |
| `R` | Re-instantiate current mode (hard state reset) |
| `ESC` | Quit Mode Studio |

---

## 3. Music Studio (`tools/music_studio.py`)

A dedicated real-time DSP and beat-tracking inspection laboratory for [`music/`](../../music/) ([`music/AudioIngestion.py`](../../music/AudioIngestion.py), [`music/DyadicMetricalAudioAnalyzer.py`](../../music/DyadicMetricalAudioAnalyzer.py), [`music/MultiBandOnsetAudioAnalyzer.py`](../../music/MultiBandOnsetAudioAnalyzer.py), [`music/StructuralNoveltyDetector.py`](../../music/StructuralNoveltyDetector.py), and [`music/Listener.py`](../../music/Listener.py)).

### 3.1 Usage & CLI Flags

```bash
# Launch with default song in songs/
python tools/music_studio.py

# Launch with a specific song (fuzzy substring match)
python tools/music_studio.py --song "daft_punk"

# Launch with live microphone input
python tools/music_studio.py --mic

# List all available songs in songs/
python tools/music_studio.py --list-songs
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--song`, `-s` | First `.mp3` | Song name or substring from `songs/`, or path to an audio file. |
| `--mic` | `False` | Use live microphone capture (`Local_Microphone`) instead of an audio file. |
| `--fps` | `60` | Target UI refresh rate (`20..120`). |
| `--list-songs` | — | Print all audio files in `songs/` and exit. |

### 3.2 Analytical Panels & Keyboard Shortcuts

1. **8-Band Mel Spectrum + 12-Tone Chromagram:** Real-time bars for `asserved_fft_band[0..7]` with peak-hold markers and `band_flux` ticks, plus the 12-semitone `smoothed_chroma_values` (`C` through `B`) and harmonic hue swatch.
2. **Scrolling Onset & Power Timeline (~8s History):** Multi-trace oscilloscope plotting `asserved_total_power`, Bass Flux (`band_flux[0] + band_flux[1]`), Mid/High Flux, and vertical event markers for `REAL` beats, `COAST` beats, `VERSE/CHORUS`, and `SONG CUT`.
3. **Anticipation Flywheel & Phase Radar:** Polar phase clock showing live `speaker_phase` ($\phi \in [0, 1)$), BPM readout, flywheel lock status (`LOCKED` / `COASTING` / `UNLOCKED`), `beat_confidence`, and `rhythm_salience`.
4. **Tempo Hypothesis Comb Distribution (`60–200 BPM`):** Bar chart of `bpm_probabilities` across the 141 candidate tempo bins from the lookahead comb-filter bank.
5. **Structural Novelty & STM vs LTM Memory:** Dual trace of raw vs asserved novelty (`combined_novelty`, `asserved_novelty`), `silence_frames`, and structural trigger counters.
6. **Collapsible Live Tuning Drawer (`TAB`):** Adjust `sensibility`, `decay_base`, `hardware_latency`, and structural thresholds in real time.

| Key | Action |
| :--- | :--- |
| `←` / `→` or `[` / `]` | Previous / Next Song |
| `TAB` | Toggle Live Parameter Tuning Drawer |
| `SPACE` | Inject synthetic Real Beat marker |
| `G` | Inject synthetic Ghost / Coasting Beat marker |
| `P` | Pause / Resume scrolling timeline plots |
| `R` | Reset analyzer & novelty state + clear history |
| `ESC` | Quit Music Studio |

---

## 4. Benchmark Runner (`research/benchmarks/run_benchmark.py`)

Runs the immutable clean-room evaluation suite across test audio tracks:
- **Usage:**
  ```bash
  python research/benchmarks/run_benchmark.py
  ```
- **Verification:**
  - Computes `F1@50ms`, `F1@70ms`, `CMLt`, `AMLt`, phase jitter, and average frame time.
  - Governed by **AXIOM-08 (Zero-Regression Gate)**.
