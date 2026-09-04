---
name: vialactee-hardware-deploy
description: Hardware abstractions, LED geometry coordinates (1,304 LEDs), Pygame simulation safety, GPIO NeoPixel drivers, and Raspberry Pi deployment procedures. Use when configuring hardware, modifying physical segment mappings, or deploying to the Raspberry Pi.
---

# Vialactée Hardware & Deployment Skill

Use this skill whenever you are modifying hardware drivers, physical LED coordinates, Pygame visualizers, or preparing/verifying deployment on the Raspberry Pi in `hardware/`, `config/segments.json`, or `setup-raspberry-pi.sh`.

## Core Guidelines & Invariants

### 1. PyGame Threading Constraints on Windows
* PyGame rendering must **always run synchronously in the main thread** on Windows.
* Inside `core/Mode_master.py`, always check `infos.get("onRaspberry")`:
  - `True` (Raspberry Pi): Offload slow hardware `.show()` calls using `loop.run_in_executor` to avoid blocking `asyncio`.
  - `False` (Windows Simulator): Call `.show()` directly on the main thread to prevent "Not Responding" UI freezes.

### 2. Physical LED Wiring & Geometry Invariant
* Total LEDs: **1,304** across 11 segments.
* **Vertical Invariant**: Vertical strips `v1`, `v2`, `v3`, `v4` are physically wired **bottom-to-top**. Their simulator step is `y -= 2` with `start_y` as the bottom-most coordinate.
* Consult [hardware_mapping.md](./references/hardware_mapping.md) for full segment coordinates and counts.

### 3. Hardware Abstractions
* Never import `neopixel` or `rpi_ws281x` at top-level outside hardware factory blocks, as this causes immediate `ImportError` crashes on non-Raspberry Pi environments.
* Use `hardware/HardwareFactory.py` to instantiate `Fake_leds`, `Rpi_NeoPixels`, or `Udp_Sender`.

### 4. Raspberry Pi Deployment Checklist
1. Ensure `infos["onRaspberry"] = True` and `infos["startServer"] = True` on deployment configs.
2. Verify Python dependencies in `requirements.txt` (`numpy`, `sounddevice`, `aiohttp`, `rpi_ws281x`).
3. If running via `systemd`, ensure ALSA / Bluetooth audio permissions are granted to the executing user.
