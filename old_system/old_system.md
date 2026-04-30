# Legacy ESP32 System Architecture overview

This document provides a highly precise technical breakdown of the 5-year-old legacy ESP32-based lighting controller (`vialactee/old_system/TribarreTests`).

## 1. Hardware & Core Environment
*   **Platform:** ESP32 Microcontroller
*   **Framework:** Arduino Core
*   **Graphics Engine:** `FastLED` library used for all pixel mapping (CHSV / CRGB manipulations) and drawing loops.
*   **Audio DSP Library:** custom implementation relying on `arduinoFFT` or built-in ADC sampling.

## 2. DSP & Audio Pipeline (`Analyser`)
The system implemented a custom audio analysis engine (`Analyser`) tailored for low-resource microcontrollers.
*   **Selective Execution:** To save CPU cycles, the `Analyser` used a boolean array (`analysingNeeds[5]`) provided by the currently active mode. It only executed specific DSP stages (e.g., FFT, beat detection) if the active mode explicitly requested them.
*   **Frequency Banding:** The FFT output was condensed into 16 discrete frequency bands (e.g., `sampleValues`, `smoothedSampleValues`).
*   **Beat & Peak Detection:**
    *   Implemented crude but effective dynamic thresholding (`samplePeak[16]`). It flagged instantaneous beats per channel.
    *   It computed global structural markers such as `asservedPower` (overall weighted volume) or total active frequency peaks.
*   **Spectral Centroid (`musicGravityCenter`):** An innovative mathematical approach converting the FFT array into a "center of gravity" of the sound, indicating whether low frequencies or high frequencies currently dominated.

## 3. Orchestration & State Machine (`Master_mode`)
The central nervous system of the project was the `Master_mode` class, which functioned as the orchestrator and state machine.
*   **Segment/Partition Management:** It could dictate whether the full LED strip was treated as a single continuous line, or logically split into multiple sub-segments (e.g., left vs. right, or third segments).
*   **Probabilistic Mode Selection:** Once a mode's timer expired, the `Master_mode` queried random values to mathematically select the next mode based on predefined weights rather than a simple sequential loop.
*   **Lifecycle Management:** Handled initializing (`activate()`), memory clearing (`deactivate()`), and triggering loop lifecycle (`update()` and `draw()`).

## 4. Transition Director
The most sophisticated mechanic of the old system was its transition engine, which completely abandoned simple "A-B crossfading" in favor of *theatrical mode changes*.
*   Transitions were triggered universally but implemented uniquely by every individual mode subclass.
*   **Two Core Transition Types:**
    *   **Black Transitions (`blackOrWhite = true`):** The Outgoing mode gracefully fades, decays its particles, or slides its coordinates down to `CHSV(0,0,0)` (black). The Incoming mode scales up its brightness or expands its size from 0.
    *   **White Transitions (`blackOrWhite = false`):** The Outgoing mode purposefully clips the brightness to maximum, pushing temperatures to 255 or forcing all LEDs sequentially to pure white. The Incoming mode reverses this phase, starting pure white and decaying down to the newly generated colors.
*   **Multi-Phase Execution:** Transitions operated as a state machine: `firstPhase`, `secondPhase`, etc., tracking `timeSinceTransition` vs `transitionTime` via continuous interpolation variables (`transiCoef`, `transitionPositionCoef`).

## 5. Animation paradigms
Unlike modern array manipulations, this C++ system relied heavily on object-oriented, iterating state-variables memory. 
*   **Physics Arrays:** Modes rarely used static `map()` functions. Instead, they kept arrays of `temperatures`, `velocities`, `accelerations`, and `positions`. 
*   Updates involved differential equations (`speed += acceleration`, `position += speed`) capped loosely by array boundaries.
*   Memory pools (`std::vector`) were routinely instanced and destroyed.
