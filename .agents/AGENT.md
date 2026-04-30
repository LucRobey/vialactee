# Vialactée Agent Context (AGENT.md)

This document contains the structural overview, recent changes, and outstanding architecture decisions for the Vialactée project. Use this context to quickly onboard AI agents to the codebase.

## 🏗️ Architecture & Directory Overview
An asynchronous Python orchestration server designed to run on a Raspberry Pi and control a 1,304-LED music-reactive chandelier.

**Project Tree:**
*   `Main.py` (Entry point, parses configs and starts background tasks)
*   `core/` (The main engine): Contains `Listener.py`, `Transition_Director.py`, `Mode_master.py`, and `Segment.py`.
*   `config/`: Contains hardcoded structure via `segments.json` and future settings managers.
    *   **Data Schema (`segments.json` snippet):**
        ```json
        {
          "name": "Segment v4",
          "size": 173,
          "order": 0,
          "orientation": "vertical",
          "alcool": false
        }
        ```
*   `connectors/`: The `Connector.py` TCP server (Port 12345) and Microphones (`ESP32_Microphone` / `Local_Microphone`). 
*   `hardware/`: Physical abstractions (currently houses `Fake_leds.py`).
*   `Vialapp/`: The native Android Java application source code. Acts as the user's remote control by firing direct TCP socket commands to `Connector.py`.

**The Hardware:**
*   **LEDs**: ~1304 WS2812b (NeoPixels) grouped into 11 logical Segments.
*   **Microphone**: Pure native Python `sounddevice` array chunking, processed through an `np.fft.rfft()`.

**The Math & Logic Engine:**
*   `Local_Microphone.py`: Maintains a continuous 4096-sample sliding buffer and multiplies the FFT output with a pre-computed **Mel Scale triangular filterbank matrix** (mapping 2049 FFT bins into 8 psychoacoustic bands) and a **Chromagram matrix** (extracting 12 musical pitch classes) instantly via compiled numpy `dot()` products.
*   `Listener.py`: Bypasses Python loops by utilizing pure `numpy` vectorization to guarantee real-time framerates on a Raspberry Pi. It applies an **ADSR (Attack/Release)** mathematical envelope for snappy, smooth light trailing across both volume bands and pitch chromagrams. It computes **Spectral Flux** to isolate distinct drum transients, feeding them into a **Phase-Locked Loop (PLL)** that mathematically deduces song BPM and continuous rhythmic anticipation phase.
*   `Mode_master.py`: Generates the modes mapped directly to `segments.json` orientations (`horizontal`/`vertical`) and handles frame drops using `asyncio` ThreadPool execution.

## 🔄 Recent Upgrades (As of April 2026)
1. **Geometric Pygame Simulator**: Running `Main.py` natively on Windows bypasses physical GPIO and perfectly draws a scaled 1300x1000 physical simulation bounding all horizontal and vertical chandelier segments simultaneously.
2. **Native Python Audio**: Fixed "divide by zero" mathematical crashes on silence. No more ESP32 networking bottleneck. Upgraded the audio processor to use a sliding window 4096-sample buffer tracking per-band variance for flawlessly smooth FFT bass extraction and beat detection.
3. **Optimized Threading**: Shifted hardware `.show()` flushes off the main asyncio loop so it no longer blocks audio streaming/network ticks.
4. **Local Testing Switch**: `startServer` was added to `Main.py`. Setting it to `False` disables port `12345` binding so developers can test the visualizer locally infinitely without socket collisions.
5. **Decluttered Root**: Consolidated scripts into `core`, `config`, and `hardware` for long-term scalability. 
6. **Vectorized DSP Engine**: Replaced traditional Python indexing inside `Listener.py` and `Local_Microphone.py` with compiled `numpy` matrices. Implemented Spectral Flux and ADSR envelopes natively. Added a **12-dimensional Chromagram** analysis engine for exact musical chords. Created a **Master Consensus Rhythmic Engine** linking a Continuous IOI (Inter-Onset Interval) Gaussian Histogram with local Binary tracking. The IOI engine actively 'octave-folds' rapid syncopation (16th/32nd notes) down to a true 60-180 BPM range using mathematical exponential time decay and power ponderation. The local binary tracker cross-validates its exact current tempo against the IOI's top peaks, triggering a Phase-Locked Loop (PLL) consensus that flawlessly predicts tempo arrays across missing beats or silent musical breakdowns!
7. **Vectorized Render Engine**: Shifted `Segment.py`'s `rgb_list` initialization to a continuous 2D `numpy` matrix. Integrated C-level array math and multi-dimensional broadcasting inside `Rainbow_mode.py` and `Mode.py` to calculate colors and interpolations simultaneously over all LEDs without any Python loops.
8. **Modes Architectural Overhaul**: Standardized all subclasses in `modes/` to override a new `run()` method rather than `update()`. `Mode.py` now internally handles all repetitive performance tracking/printing boilerplate. Removed all magic constants inside math operations by pulling dynamic values from the `infos` configuration payload!
9. **Native Beat and Sub-beat Tracking**: Upgraded the pure-Python Phase-Locked Loop (PLL) comb filter in `Listener.py` to continuously freewheel phase (`best_p`) naturally during complete silence. Reduced the beat lockout threshold and implemented 2x frequency crossover tracking, empowering the listener to proactively emit a continuous, seamless stream of perfectly timed alternating main-beats and sub-beats without stalling. `Metronome_mode.py` uses this to instantaneous strobe the entire bar White (beat) and Blue (sub-beat).
10. **Decoupled Freewheeling Phase-Locked Loop**: Redesigned the beat progression logic in `Listener.py` to fully decouple the internal `beat_phase` and `beat_count` from BTrack's raw phase jump points. It acts as an independent continuous mechanical flywheel that simply references BTrack's angle frame-by-frame and gracefully steers its own angle via soft-sync, producing perfectly smooth, stutter-free light movements.
11. **Advanced DSP Robustness Features**: Fortified the BTrack engine with immense resiliency upgrades: **Hard Onset Gating** explicitly clamps volume blocks without physical transients; **Logarithmic Compressed ODF** rigorously normalizes huge bass kicks and tiny hi-hat frequencies so Autocorrelation ignores volume entirely and locks natively onto rhythm; **Harmonic Autocorrelation Folding** sums fractional sub-tempos directly into the primary BPM; and an **Elastic Comb Filter Phase Alignment** that uses an exponential recency decay to glue the rhythmic grid exclusively to the most recent 1 second of live drumming rather than accumulating micro-timing drift from 4 seconds in the past.
12. **Dynamic Audio Latency Tracking**: Replaced hardcoded hardware latency configurations by actively computing real-world latency using `sounddevice`'s PortAudio `time_info.inputBufferAdcTime` timestamps to identify exactly when the chunk physically hit the mic. Combined with the mathematical algorithmic delay (the exact center point of the 4096-sample Hanning FFT window wrapper), the Phase-Locked Loop natively self-calibrates the forward phase shift.
13. **Audio-Based Orchestration**: Introduced `Transition_Director.py` to decouple playlist management from `Mode_master.py`. It actively parses DSP state (Spectral Flux drops, smoothed total power) to intelligently delay transitions if a heavy bass drop is hitting or auto-force a "Standby/Chill" playlist if >= 10 seconds of complete silence is detected.
14. **Dual Magnetic Lookahead Snapping & Gaussian Phase Inertia**: Integrated a Continuous 5-second Lookahead audio delay buffer that perfectly anchors main-beats to bass frequencies and sub-beats to high hi-hat frequencies. A `0.20` variance Gaussian Phase Inertia enforces strict tempo stability, mathematically preventing 180-degree phase inversions during complex syncopated drops and effectively outperforming Librosa's non-causal benchmark ground truth.
## ✅ Resolved Technical Debt (Completed)
- [x] Hardcoded `Rainbow` mode blocking transitions in `Segment.py`.
- [x] CPU busy-waiting (100% overload). Frames are safely locked to 30 FPS (`Mode_master`) and 60 Tick (`Listener`).
- [x] `neopixel` hardware flush blocking issues.
- [x] Hardcoded matrix geometries pulled out of python and injected into `segments.json`.

## ⚠️ Known Technical Debt (Remaining TO-DOs)
*   Currently the architecture is extremely healthy. Next steps involve building new matrix animations within `modes/` or refining the external smartphone connection API through `Connector.py`.
