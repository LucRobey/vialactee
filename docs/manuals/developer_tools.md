# Developer Tools & Offline Studios Guide

> **Location:** `docs/manuals/developer_tools.md` (Tier 2 Operational Manual)  
> **Source Directory:** [`tools/`](../../tools/), [`hardware/Fake_leds.py`](../../hardware/Fake_leds.py), [`research/benchmarks/`](../../research/benchmarks/)  
> **Target Audience:** Developers, DSP Researchers, and Visual Mode Designers

This manual covers the offline graphical workbenches, interactive studios, and simulation tools available in Vialactée. Both studios in `tools/` run completely standalone on Windows, macOS, or Linux — no ESP32, no Raspberry Pi, and no web server required.

---

## 1. The Pygame Visualizer (`Fake_leds.py`)

When running `Main.py` on a PC (`"HARDWARE_MODE": "simulation"` or `"auto"`), the system spawns `hardware/Fake_ESP32.py`, which renders into `hardware/Fake_leds.py`.
- **Dynamic Topology:** Automatically scales and renders all active chandelier segments according to `config/segments_*.json`.
- **Audio HUD:** When `"show_music_analyser_panel": true`, overlays real-time FFT bands, spectral flux, instant volume, BPM estimates, and flywheel beat indicators on top of the chandelier display.

---

## 2. Mode Studio (`tools/mode_studio.py`)

A hot-reloading visual laboratory for creating, tuning, and debugging light modes in [`modes/`](../../modes/).

### 2.1 Usage & CLI Flags

```bash
# Launch with the first song in songs/ and the first registered mode
python tools/mode_studio.py

# Launch a specific song and mode (fuzzy substring match on both)
python tools/mode_studio.py --song "stromae" --mode "Impact Shockwave"

# Custom LED count + explicit analyzer model
python tools/mode_studio.py -s 2 -m "Chromatic Chaser" --leds 120 --model DyadicMetricalAudioAnalyzer
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--song`, `-s` | First track in `songs/` | Song filename substring, 1-based index (`1-9`), or path to an audio file. |
| `--mode`, `-m` | First mode in `config/modes.json` | Mode name or substring (e.g. `"shockwave"`, `"chaser"`). |
| `--leds`, `-l` | `80` | Number of simulated LEDs on the virtual strip. |
| `--model` | `DyadicMetricalAudioAnalyzer` | Audio analyzer model (`DyadicMetricalAudioAnalyzer`, `MultiBandOnsetAudioAnalyzer`, `AudioAnalyzer`). |

### 2.2 HUD Layout (`1480 × 940`)

- **Header (`54 px`):** Current mode name, orientation badge (`HORIZONTAL` / `VERTICAL`), song title, analyzer dropdown (`DyadicMetrical` / `MultiBandOnset` / `Legacy`), `Sens`, `Sync` offset (`ms`), and per-frame `mode.update()` execution time in `ms` (color-coded against the **AXIOM-01** frame budget).
- **Card 0 — Virtual LED Strip (`150 px`):** Simulated glowing LEDs (`80` default) rendered in horizontal strip or vertical column layout, plus an interactive **Song Timeline Scrubber** (click anywhere to seek).
- **Card 1 — 8-Band Mel Spectrum (`145 px`):** Live normalized `asserved_fft_band[0..7]` bars (`Sub-Bass` through `Brilliance`) with peak-hold markers and `band_flux` transient bars.
- **Card 2 — Mode Settings (`145 px`):** Auto-generated interactive controls (`slider`, `toggle`, `list`) from the active mode's `get_settings_schema()`, with a **Reset Defaults** button.
- **Card 3 — Musical Context & Mood (`210 px`):**
  - **Left (`30%`):** Macro `scene` badge (`CHILL` / `GROOVE` / `BUILDUP` / `DROP_IMPACT`), `rhythm_salience`, `beat_trust`, and live `mood/` palette swatches (`mood_colors[0..3]` + `highlight_color`) with a clickable **Mood selector dropdown**.
  - **Center (`44%`):** **6-Second Dual Trace** of `energy` (green) and `tension` (amber) with event flags (`DROP!`, `DROP SOON`, `CUT`).
  - **Right (`26%`):** **Drop Detector / Override Tester** (`[B] Test Buildup (4s)`, `[D] Test Drop Now`, `[C] Reset CD`) and **12-Pitch Chromagram** (`C`..`B`).
- **Card 4 — Rhythm & Tempo (`150 px`):** Live BPM readout, **Phase Dial** ($\phi \in [0, 1)$), `REAL` vs `COAST` beat flash indicators, **6-Second Beat & Onset Stream**, and **Tempo Comb Probability Curve (`60–200 BPM`)**.

### 2.3 Keyboard Shortcuts (`mode_studio.py`)

| Key | Action |
| :--- | :--- |
| `[R]` | **Hot-Reload** the current mode's `.py` file from disk (`importlib.reload`) without restarting audio |
| `[Space]` | Pause / Resume audio playback |
| `[↑]` / `[↓]` | Cycle through all 13 modes in `config/modes.json` |
| `[←]` / `[→]` | Seek `-5s` / `+5s` in the active song (or click the timeline bar) |
| `[B]` / `[D]` / `[C]` | Trigger synthetic `BUILDUP` (`4s` ramp -> drop) / immediate `DROP_IMPACT` / reset drop cooldown |
| `[N]` / `[P]` | Next / Previous song in `songs/` |
| `[1]`–`[9]` | Jump directly to song `#1`–`#9` |
| `[+]` / `[-]` | Increase / Decrease audio `sensibility` (`5`..`100`) |
| `[O]` | Cycle strip orientation override (`Auto` -> `Horizontal` -> `Vertical`) |
| `[K]` / `[L]` | Adjust audio-visual sync offset `-10 ms` / `+10 ms` (`[\]` resets to `0 ms`) |
| `[Ctrl+B]` / `[Ctrl+L]` / `[Ctrl+S]` / `[Ctrl+T]` / `[Ctrl+M]` | Toggle choreography mute channels (`beat`, `level`, `spectrum`, `transient`, `macro`) via `DriverMuteProxy`; `[Ctrl+0]` clears all mutes |
| `[Esc]` | Quit Mode Studio |

---

## 3. Music Studio (`tools/music_studio.py`)

A full-screen real-time DSP and beat-tracking inspection laboratory for [`music/`](../../music/) ([`music/AudioIngestion.py`](../../music/AudioIngestion.py), [`music/DyadicMetricalAudioAnalyzer.py`](../../music/DyadicMetricalAudioAnalyzer.py), [`music/MultiBandOnsetAudioAnalyzer.py`](../../music/MultiBandOnsetAudioAnalyzer.py), [`music/StructuralNoveltyDetector.py`](../../music/StructuralNoveltyDetector.py), [`music/MusicalContextEngine.py`](../../music/MusicalContextEngine.py), and [`music/Listener.py`](../../music/Listener.py)).

### 3.1 Usage & CLI Flags

```bash
# Launch with the first song in songs/ and the default analyzer
python tools/music_studio.py

# Launch a specific song and analyzer model
python tools/music_studio.py --song "losing" --model DyadicMetricalAudioAnalyzer
```

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--song`, `-s` | First track in `songs/` | Song filename substring, 1-based index (`1-9`), or path to an audio file. |
| `--leds`, `-l` | `80` | Number of LEDs simulated inside the internal `Listener`. |
| `--model`, `-m` | `DyadicMetricalAudioAnalyzer` | Initial analyzer model (`DyadicMetricalAudioAnalyzer`, `MultiBandOnsetAudioAnalyzer`, `AudioAnalyzer`). |

### 3.2 Analytical Panels (`1600 × 980`)

1. **Header & Song Scrubber:** Active song, clickable **Analyzer Model selector**, live `Sens`, `Sync` offset (`ms`), `[T] Tune Params` button, and interactive seek bar.
2. **Panel 1 — 8-Band Mel Spectrum (`asserved_fft_band` & `band_flux`):** Normalized `0..1` band energy bars, peak-hold indicators, half-wave rectified spectral flux, and `GM` / `LM` / `Power` / `Flux` summary meters.
3. **Panel 2 — 12-Pitch Chromagram (`smoothed_chroma_values`):** Real-time pitch-class energy across all 12 semitones (`C` through `B`), dominant pitch readout, and harmonic color swatch.
4. **Panel 3 — Anticipation Flywheel & Phase Clock:** Polar phase radar ($\phi \in [0, 1)$), live BPM, `LOCKED` / `COASTING` status badge, `Confidence` & `Salience` bars, `REAL BEAT` / `COAST BEAT` / `VERSE/CHORUS` / `SONG CUT` lamps, and **Tempo Hypothesis Distribution (`60–200 BPM`)**.
5. **Panel 4 — 32-Band Log-Mel Filterbank (`mel32_bands` & `mel32_flux`):** High-resolution 32-band log-Mel spectrogram and onset flux streams feeding the 4-stream rhythm engine.
6. **Panel 5 — 4-Stream Percussive Onsets (`8s` Scrolling History):** Scrolling oscilloscope for **Kick (`30–140 Hz`)**, **Snare (`140–1.2 kHz`)**, **Hi-Hat (`3–12 kHz`)**, **Mid/Harmonic**, and fused **Combined ODF** with vertical beat markers.
7. **Panel 6 — Structural Novelty & Musical Context (`8s` Scrolling History):** Scrolling STM/LTM structural novelty trace (`asserved_novelty`), macro `scene` state, `energy` & `tension` curves, and `drop_countdown` telemetry.
8. **Live Parameter Tuner Overlay (`[T]`):** Interactive slider drawer exposing `12` live DSP & flywheel parameters (`sensibility`, `LOCK_THRESHOLD`, `COAST_THRESHOLD`, `PHASE_CORRECTION_STRENGTH`, `ONSET_SNAP_THRESHOLD`, `REAL_BEAT_FLUX_THRESHOLD`, `NOVELTY_VERSE_CHORUS_THRESHOLD`, `NOVELTY_SONG_CHANGE_THRESHOLD`, `STREAM_WEIGHT_KICK`, `STREAM_WEIGHT_SNARE`, `STREAM_WEIGHT_HAT`, `STREAM_WEIGHT_MID`) with `[D]` Reset Defaults.

### 3.3 Keyboard Shortcuts (`music_studio.py`)

| Key | Action |
| :--- | :--- |
| `[Space]` | Pause / Resume audio playback |
| `[←]` / `[→]` | Seek `-5s` / `+5s` in the active song (or click the timeline bar) |
| `[N]` / `[P]` | Next / Previous song in `songs/` |
| `[1]`–`[9]` | Jump directly to song `#1`–`#9` |
| `[M]` | Cycle analyzer model (`DyadicMetricalAudioAnalyzer` -> `MultiBandOnsetAudioAnalyzer` -> `AudioAnalyzer`) |
| `[T]` | Toggle Live Parameter Tuner overlay (`[D]` inside tuner resets defaults) |
| `[+]` / `[-]` | Increase / Decrease audio `sensibility` (`5`..`100`) |
| `[K]` / `[L]` | Adjust audio-visual sync offset `-10 ms` / `+10 ms` (`[\]` resets to `0 ms`) |
| `[Esc]` | Close tuner overlay or quit Music Studio |

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

---

## 5. Choreography Stimulus Matrix (`tools/choreography_matrix.py`)

Evaluates all 13 registered modes in [`config/modes.json`](../../config/modes.json) against a deterministic synthetic music stimulus under selective driver mutes ([`utils/driver_mute.py`](../../utils/driver_mute.py)) to verify **Law 7: One Lead Timescale** ([`docs/contracts/mode_contract.md`](../contracts/mode_contract.md#7-one-lead-timescale-the-choreography-doctrine)).

### 5.1 Usage & CLI Flags

```bash
# Run the 13 x 4 choreography matrix at the canonical 8-band configuration
python -m tools.choreography_matrix

# Run diagnostic evaluation at 16 FFT bands
python -m tools.choreography_matrix --bands 16
```

Both the CLI report and the CI suite ([`tests/governance/test_mode_choreography.py`](../../tests/governance/test_mode_choreography.py)) share a single configuration (`MATRIX_CONFIG = {"num_leds": 40, "warmup_frames": 30, "eval_frames": 120}`).

### 5.2 Matrix Columns & Metrics

| Column | Definition |
| :--- | :--- |
| `Lead` / `Sec` | The mode's declared `LEAD` and `SECONDARY` driver from `DRIVERS = ("beat", "level", "spectrum", "transient")` in [`utils/choreography.py`](../../utils/choreography.py). |
| `R_std(full)` | Mean per-LED temporal standard deviation across the evaluation window with all channels active (amplitude budget metric). |
| `R_std(-lead)` | `R_std` when only the mode's declared `LEAD` driver is muted. |
| `R_std(-sec)` | `R_std` when only the mode's declared `SECONDARY` driver is muted (`== R_std(full)` when `SECONDARY == ()`). |
| `R_std(-all)` | `R_std` when all 5 mute channels (`beat`, `level`, `spectrum`, `transient`, `macro`) are muted simultaneously (captures constant non-audio drift). |
| `d(lead)` / `d(sec)` | Ablation drop `R_std(full) - R_std(-lead)` and `R_std(full) - R_std(-sec)`. |
| `R_diff` | Mean per-LED frame-to-frame absolute delta under `full` (velocity / busyness indicator). |
| `d(beat..transient)` | Second table showing single-driver ablation `R_std(full) - R_std(-d)` for each of the 4 drivers. |

### 5.3 Calibrated Thresholds (`f`, `g`), `CONFORMING_MODES_PHASE_4A`, & Recalibration

In [`tests/governance/test_mode_choreography.py`](../../tests/governance/test_mode_choreography.py), every mode listed in `CONFORMING_MODES_PHASE_4A` must satisfy three hard assertions at 8 bands:
1. **Lead dominance:** `d(lead)` is strictly the largest single-driver ablation among `{beat, level, spectrum, transient}`.
2. **Lead audio-budget fraction (`f = 0.30`):** `d(lead) >= f * (R_std(full) - R_std(-all))`. Subtracting `R_std(-all)` cancels constant non-audio animation drift so `f` measures the lead driver's share of **audio-driven variance**.
3. **Secondary retention (`g = 0.65`):** When `SECONDARY` is declared, `R_std(-sec) >= g * R_std(full)`, ensuring that muting the secondary driver alone leaves at least 65% of the full amplitude budget intact.

Modes not yet in `CONFORMING_MODES_PHASE_4A` are pre-redesign modes tracked diagnostically until their redesign batches land.

**How to recalibrate:** `CALIBRATED_FOR` in `test_mode_choreography.py` locks `(SYNTHETIC_CLIP_VERSION, DEFAULT_NB_BANDS, MATRIX_CONFIG)`. If you intentionally modify the synthetic stimulus clip (`step_synthetic_music`), default band count, or `MATRIX_CONFIG`:
1. Increment `SYNTHETIC_CLIP_VERSION` in `tools/choreography_matrix.py`.
2. Run `python -m tools.choreography_matrix` (with `PYTHONHASHSEED=0`), inspect the `13 x 4` table, and verify `CALIBRATED_LEAD_FRACTION_F` and `CALIBRATED_SEC_RETAINED_G` across all modes in `CONFORMING_MODES_PHASE_4A`.
3. Update `CALIBRATED_FOR` (and `f` / `g` if required) in `tests/governance/test_mode_choreography.py`.
