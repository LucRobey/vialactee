---
name: vialactee-project
description: Central knowledge, architecture boundaries, and execution rules for the Vialactée interactive LED chandelier project. Use when modifying modes, segment geometries, or project orchestration.
---

# Vialactée Project Skill

Use this skill whenever you are making changes to the Vialactée music-reactive LED chandelier repository. It contains the strict rules and architectural constraints required bounds to safely work on the project.

## Directory Structure
The workspace is cleanly divided:
- `Main.py`: The async orchestration entry point.
- `core/`: The math and execution engine (`Mode_master.py`, `Transition_Director.py`, `Listener.py`, `Segment.py`).
- `config/`: The JSON mappings for physical structures (`segments.json`, `Configuration_manager.py`).
- `hardware/`: Physical abstractions (like the `Fake_leds.py` visualizer).
- `connectors/`: Asynchronous integrations (Connector server, `Local_Microphone`, `ESP32_Microphone`).

## Core Execution Rules

### 1. PyGame Threading Constraints
PyGame is strictly bound to the **main thread** on Windows. 
Whenever you invoke `.show()` in `Mode_master.py`, you **must** check `infos.get("onRaspberry")`:
- If `True` (Raspberry Pi): Use `loop.run_in_executor` to offload the slow `neopixel.show()` calls and prevent `asyncio` from blocking.
- If `False` (Local Windows Sim): Simply call `.show()` synchronously in the main thread to prevent PyGame from freezing with a "Not Responding" error.

### 2. Audio Processing Math (Vectorized DSP Engine)
The `Local_Microphone` relies exclusively on native `sounddevice` streams coupled with `numpy.fft.rfft`.
Instead of arbitrary frequency band limits with slow Python loops, the architecture uses pre-computed **Mel Scale** and **Chromagram** transformation matrices to map 2049 FFT bins exactly to the 8-band psychoacoustic human hearing scale and 12-note musical pitch classes using lightning-fast compiled `np.dot()` products.
`Listener.py` handles the beat detection, tempo expectation (Phase-Locked Loop), chroma tracking, and visual scaling purely through vectorized `numpy` manipulation. It applies an **ADSR (Attack/Release)** envelope for snappy visual attacks but silky smooth fade-outs over both volume bands and pitch chromagrams. Beat detection runs via a **Spectral Flux** algorithm, masked tightly by **Hard Onset Gating** to explicitly obliterate ambient volume and only pass exact transients. This gated flux is subjected to **Logarithmic Compression** (`np.log1p`), mathematically equalizing 2000-volume kickdrums and 50-volume cymbals so that Autocorrelation solely processes structural rhythm instead of volume. This signal is processed into an **Autocorrelation Buffer** implementing **Harmonic Octave Folding**, which mathematically folds fractional sub-tempos directly into the primary target BPM so high-speed drumming inherently boosts core phase alignment instead of breaking it. The local binary tracker cross-validates its exact current tempo against an **Elastic Comb Filter**—which uses an exponential decay curve against chronological buffer depth alongside a geometric Gaussian fractional window—forcing phase alignment to permanently lock onto the most recent 1-second of live instrumentation without dragging off-grid drift from the past. This triggers a Phase-Locked Loop (PLL) consensus that flawlessly predicts tempo arrays across missing beats or silent musical breakdowns!
**Dynamic Latency Tracking**: Audio latency is natively evaluated by polling `time_info.inputBufferAdcTime` directly from `sounddevice`'s C-thread inside `Local_Microphone`, capturing precisely when the audio chunk registered on the analog boundary. This `time.time()` marker is inherently combined with the exact geometric peak representation limit of a full symmetric Hanning window block, allowing the PLL to programmatically calculate physical time lag natively without relying on a rigid tuning configuration, eliminating external visual desynchronizations.
**Audio-Based Transitions**: `Mode_master` delegates all playlist progression decisions to `Transition_Director.py`. This Oracle directly reads `Listener`'s `band_peak` transients and `smoothed_total_power` to delay standard transitions during heavy musical drops and automatically force Standby playlists during long silences.
**Never modify the floating point division bounds without asserting `total > 0` safety nets** (and using safe division like `np.where(diff == 0, 1.0, diff)`) to prevent divide-by-zero crashes on complete silence.
**Important PLL Convention**: The beat tracking logic uses a **Continuous Freewheeling Soft-Sync PLL**. The tracker completely decouples the mode-facing `beat_phase` and `beat_count` from raw, jumpy BTrack phase events. Instead, `beat_phase` acts as an independent continuous mechanical flywheel incrementing perfectly in real-time according to `self.bpm` and frame `delta_time`. It then gently pulls its angle toward BTrack's raw phase math via soft-sync. This guarantees flawlessly smooth normalized fractional float [0.0->1.0] representations of the phase for use inside visually-dependent Modes (like the strobing effects in `Metronome_mode.py`) that never abruptly skip.

### 3. LED Segment Mapping & Visualizer Coordinates
The chandelier consists of `1,304` total LEDs mapped sequentially.
When updating the PyGame simulator (`hardware/Fake_leds.py`), the drawing loops use:
- `"horizontal"`: `x += 2`
- `"vertical"`: `y += 2` (Top-to-Bottom)
- `"vertical_up"`: `y -= 2` (Bottom-to-Top)

**IMPORTANT**: All physical vertical LED strips (`v1`, `v2`, `v3`, `v4`) are wired from bottom to top! Their geometric definitions in `Fake_leds.py` must use the `"vertical_up"` orientation, and their `start_y` corresponds geometrically to their **bottom-most coordinates**.

### 4. Port Collisions Avoidance
When testing locally, `Main.py` leverages an `infos` dictionary config block. `startServer` is mapped to `False` to prevent the `connectors/Connector.py` aiohttp remote control server from continuously failing to bind to `0.0.0.0:8080` on successive `ctrl+c` / script restarts. If you are developing a connector feature, explicitly switch it to `True`.

### 5. Code Style
Always preserve the user's aliased import conventions exactly as they exist:
```python
import core.Mode_master as Mode_master
import hardware.Fake_leds as Fake_leds
```
Do not refactor to `from core import Mode_master` unless specifically requested.

### 6. DSP and Visual Vectorization
For extreme performance on the Raspberry Pi:
- **Audio Processing**: `Listener.py` and `Local_Microphone.py` use compiled `numpy` matrices for tasks like Mel Scale filtering, 12-dimensional Chromagram extraction, Spectral Flux calculation, high-precision IOI (Inter-Onset Interval) tempo histograms leveraging time/power exponential ponderation, Autocorrelation, Master Consensus Phase-Locked Loop (PLL) anticipatory tracking, and ADSR enveloping, completely avoiding slow Python loops.
- **Rendering Modes**: When writing or updating visual modes in `modes/`, you must override the `run(self)` method (DO NOT override `update()`, which handles timing tracking automatically). Use NumPy vectorization for all color mathematics. **Do not iterate over `led_index` with Python `for` loops.** Instead, precompute state matrices (e.g., vectorized arrays for Hues/Saturations) and compute targeted colors using `RGB_HSV.fromHSV_toRGB_vectorized(h, s, v)` (which will broadcast scalars to array shapes automatically!).
- **`rgb_list` Data Structure**: `Segment.py` defines `rgb_list` natively as a 2D `numpy.ndarray` shaped `(len(indexes), 3)`. Modes should use the base `self.smooth_segment_vectorized(ratio, start, stop, target_array_or_color)` or `self.fade_to_black_segment_vectorized(ratio, start, stop)` methods for applying fade logic. This smooths securely against persistent memory state rather than volatile hardware arrays, preventing exponential dimming bugs!
- **Magic Config Injection**: Ensure standalone tuning parameters (e.g., blending ratios or brightness multipliers) are fetched purely via `infos.get("custom_var_name", default_val)` instead of hard-coding localized magic numbers into the `.py` files.
