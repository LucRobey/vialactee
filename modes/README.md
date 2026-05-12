# Visual Modes (`/modes/`)

The `modes` directory contains the creative visual algorithms for the chandelier. Each file is an animation subclass.

## Key Components:

- **`Mode.py`**: The base class for all visual effects. It provides shared utility functions and enforces a strict contract between the `Mode_master` and the mode.
- **Animation Files (e.g., `Rainbow_mode.py`, `Metronome_mode.py`, `Matrix_rain_mode.py`)**: Individual visual routines. They take in the current audio state (like `bass_flux` or `beat_phase`) and calculate an RGB state for every LED.

## The Architecture Contract

### 1. `run()` vs `update()`
All mode subclasses must override `run()`, **not** `update()`.
*   `Mode.update()` is a final method on the base class that automatically handles performance profiling and boilerplate updates. It internally calls `self.run()`.
*   If you override `update()` inside a mode subclass, you will break the performance profiling pipeline.

### 2. The `rgb_list` Array
The visual canvas for a segment is managed natively as a 2D numpy matrix: `self.rgb_list` (shape: `[number_of_leds, 3]`). 
Modes operate by slicing and mutating this matrix directly, taking advantage of C-level vectorization to compute thousands of LEDs without Python loops.

### 3. The `infos` Payload
Variables that control math formulas (like sensitivities, decay rates, and physical constraints) are passed through the `self.infos` dictionary rather than being hardcoded. 
`self.infos` is a merged payload containing the global `app_config.json` parameters as well as dynamic `modeSettings` injected from the active configuration.

### 4. Vectorized Smoothing
To interpolate harsh jumps in data, modes utilize the base class's `self.smooth_segment_vectorized()` utility method. This function instantly applies exponential moving average decay matrices to the entire `rgb_list`, maintaining fluidity.

## How it works:
These scripts leverage vectorized `numpy` operations to calculate complex visual patterns simultaneously across thousands of LEDs without slow Python loops. They react dynamically to the music's BPM, frequency intensities, and phase locked loops provided by the `Listener`.
