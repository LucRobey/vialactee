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
