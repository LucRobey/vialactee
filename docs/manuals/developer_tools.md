# Developer Tools & Offline Studios Guide

> **Location:** `docs/manuals/developer_tools.md` (Tier 2 Operational Manual)  
> **Target Audience:** Developers, DSP Researchers, and Visual Mode Designers

This manual covers the offline graphical workbenches and simulation tools available in Vialactée.

---

## 1. The Pygame Visualizer (`Fake_leds.py`)

When running `Main.py` on a PC (`"HARDWARE_MODE": "simulation"` or `"auto"`), the system spawns `hardware/Fake_ESP32.py`, which renders into `hardware/Fake_leds.py`.
- **Dynamic Topology:** Automatically scales and renders all active chandelier segments according to `config/segments_*.json`.
- **Audio HUD:** When `"show_music_analyser_panel": true`, overlays real-time FFT bands, spectral flux, instant volume, BPM estimates, and flywheel beat indicators on top of the chandelier display.

---

## 2. Mode Studio (`mode_studio.py`)

A focused laboratory tool for designing, tuning, and profiling individual animation modes:
- **Usage:**
  ```bash
  python mode_studio.py
  ```
- **Features:**
  - Isolates a single segment and mode.
  - Allows injecting synthetic audio transients or playing an audio file loop.
  - Exposes mode tuning sliders defined in `get_settings_schema()`.
  - Visualizes frame computation times to ensure compliance with AXIOM-01 ($\le 20.0\text{ ms}$).

---

## 3. Music Studio (`music_studio.py`)

An advanced offline MIR laboratory for inspecting audio feature extraction:
- **Usage:**
  ```bash
  python music_studio.py
  ```
- **Features:**
  - Displays the 32 Mel onset derivative streams ($y_{\text{kick}}, y_{\text{snare}}, y_{\text{hat}}, y_{\text{mid}}$).
  - Visualizes real-time Pearson template bank correlation curves across tempo octaves.
  - Shows speaker lookahead back-projection phase and real-beat vs dropped-beat classification.

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
