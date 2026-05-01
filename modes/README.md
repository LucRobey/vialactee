# Visual Modes (`/modes/`)

The `modes` directory contains the creative visual algorithms for the chandelier. Each file is an animation subclass.

## Key Components:

- **`Mode.py`**: The base class for all visual effects. It enforces the implementation of a `run()` method and provides shared utility functions.
- **Animation Files (e.g., `Rainbow_mode.py`, `Metronome_mode.py`, `Matrix_rain_mode.py`)**: Individual visual routines. They take in the current audio state (like `bass_flux` or `beat_phase`) and calculate an RGB state for every LED.

## How it works:
These scripts leverage vectorized `numpy` operations to calculate complex visual patterns simultaneously across thousands of LEDs without slow Python loops. They react dynamically to the music's BPM, frequency intensities, and phase locked loops provided by the `Listener`.
