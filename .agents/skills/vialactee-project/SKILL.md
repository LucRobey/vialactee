---
name: vialactee-project
description: Central knowledge, architecture boundaries, and execution rules for the Vialactée interactive LED chandelier project. Use when modifying modes, segment geometries, or project orchestration.
---

# Vialactée Project Skill

Use this skill whenever you are making changes to the Vialactée music-reactive LED chandelier repository. It contains the strict rules and architectural constraints required bounds to safely work on the project.

## Directory Structure
The workspace is cleanly divided:
- `Main.py`: The async orchestration entry point.
- `core/`: The math and execution engine (`Mode_master.py`, `Listener.py`, `Segment.py`).
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
`Listener.py` handles the beat detection, tempo expectation (Phase-Locked Loop), chroma tracking, and visual scaling purely through vectorized `numpy` manipulation. It applies an **ADSR (Attack/Release)** envelope for snappy visual attacks but silky smooth fade-outs over both volume bands and pitch chromagrams. Beat detection runs via a **Spectral Flux** algorithm, strictly calculating the positive difference in energy between frames to isolate sharp drum transients. These transients are fed into a **Master Consensus** engine consisting of three parallel trackers: a 4-second Autocorrelation buffer, an **IOI (Inter-Onset Interval) Gaussian Histogram**, and a classic Binary tracker. The IOI logically tracks massive drum syncopation (like 16th and 32nd fractions) and physically 'octave folds' them strictly back within an approved 60-180 BPM range, weighting all votes dynamically using exponential time decay (`np.exp(-dt)`) and physical drum impact (`np.sqrt(power)`). The binary tracker validates its transient interval dynamically against the Continuous IOI's top Gaussian peaks, forging a mathematical consensus map to predict tempo continuity indefinitely across rhythmically quiet musical breakdowns!
**Never modify the floating point division bounds without asserting `total > 0` safety nets** (and using safe division like `np.where(diff == 0, 1.0, diff)`) to prevent divide-by-zero crashes on complete silence.

### 3. LED Segment Mapping & Visualizer Coordinates
The chandelier consists of `1,304` total LEDs mapped sequentially.
When updating the PyGame simulator (`hardware/Fake_leds.py`), the drawing loops use:
- `"horizontal"`: `x += 2`
- `"vertical"`: `y += 2` (Top-to-Bottom)
- `"vertical_up"`: `y -= 2` (Bottom-to-Top)

**IMPORTANT**: All physical vertical LED strips (`v1`, `v2`, `v3`, `v4`) are wired from bottom to top! Their geometric definitions in `Fake_leds.py` must use the `"vertical_up"` orientation, and their `start_y` corresponds geometrically to their **bottom-most coordinates**.

### 4. Port Collisions Avoidance
When testing locally, `Main.py` leverages an `infos` dictionary config block. `startServer` is mapped to `False` to prevent the `connectors/Connector.py` TCP remote control server from continuously failing to bind to `0.0.0.0:12345` on successive `ctrl+c` / script restarts. If you are developing a connector feature, explicitly switch it to `True`.

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
