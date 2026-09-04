---
name: vialactee-hardware-deploy
description: Hardware abstractions, LED geometry coordinates (full: 1,304 LEDs, small: 249 LEDs), dynamic channel allocation, Pygame simulation safety, GPIO NeoPixel drivers, and Raspberry Pi deployment procedures.
---

# Vialactée Hardware & Deployment Skill

Use this skill whenever you are modifying hardware drivers, physical LED coordinates, Pygame visualizers, or preparing/verifying deployment on the Raspberry Pi in `hardware/`, `config/segments_full.json`, `config/segments_small.json`, or `setup-raspberry-pi.sh`.

## Core Guidelines & Invariants

### 1. PyGame Simulation Architecture (Gen 3)
* When `HARDWARE_MODE == "simulation"`, `HardwareFactory` spawns `Fake_ESP32.py` as an **isolated background subprocess**.
* `Mode_master` runs strictly headless and streams frames over UDP (`127.0.0.1:9001/9002`), completely decoupling visual rendering and OS window events from the audio-processing loop.
* `Fake_leds.py` dynamically reconstructs its geometry directly from `segments_full.json` or `segments_small.json`, establishing a single source of truth.

### 2. Hardware Profiles & Physical LED Wiring
* **`full` Profile**: 1,304 LEDs across 11 segments on 2 channels (`segs_1`: 785 LEDs, `segs_2`: 519 LEDs).
  - **Vertical Invariant**: Vertical strips `v1`, `v2`, `v3`, `v4` are physically wired **bottom-to-top**. Their simulator step is `y -= 2` with `start_y` as the bottom-most coordinate.
* **`small` Profile**: 249 LEDs across 3 segments on 1 channel (`segs_1`: `s1` 49, `s2` 108, `s3` 92, all vertical).
* Consult [hardware_mapping.md](./references/hardware_mapping.md) for full segment coordinates, UI layout mappings, and channel specs.

### 3. Hardware Abstractions & Dynamic Channel Provisioning
* Never import `neopixel` or `board` at top-level outside hardware factory blocks, as this causes immediate `ImportError` crashes on non-Raspberry Pi environments.
* `hardware/HardwareFactory.py` inspects `_get_channel_specs(infos)` to dynamically determine channel count and LED sizes from the active segment configuration. Returns a tuple of hardware instances (e.g. `(leds1,)` or `(leds1, leds2)`).
* Primary production architecture uses `Udp_Sender` (network ESP32 over Wi-Fi). `Rpi_NeoPixels` (`adafruit-circuitpython-neopixel`) is maintained as a legacy fallback.

### 4. Raspberry Pi Deployment Checklist
1. Ensure `infos["onRaspberry"] = True` and `infos["startServer"] = True` on deployment configs.
2. Verify Python dependencies in `requirements.txt` (`numpy`, `sounddevice`, `aiohttp`, `adafruit-circuitpython-neopixel`).
3. If running via `systemd`, ensure ALSA / Bluetooth audio permissions are granted to the executing user.
