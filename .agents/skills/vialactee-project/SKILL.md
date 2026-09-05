---
name: vialactee-project
description: Central knowledge, architecture boundaries, and execution rules for the Vialactée interactive LED chandelier project. Use when modifying core orchestration, coordinating multiple domains, or onboarding to the codebase.
---

# Vialactée Project & Architecture Master Skill

Use this skill as the primary architectural authority for the Vialactée music-reactive LED chandelier repository. It defines global system invariants, threading models, and indexes the specialized domain skills.

---

## 1. Directory Structure

* `Main.py`: The asynchronous orchestration entry point.
* `core/`: The math and execution engine (`Mode_master.py`, `CommandRouter.py`, `PresetRepository.py`, `Transition_Director.py`, `Transition_Engine.py`, `Listener.py`, `AudioAnalyzer.py`, `AudioIngestion.py`, `Segment.py`).
* `modes/`: Visual light animation modes inheriting from `modes.Mode`.
* `config/`: Hardware profiles (`hardware_profile` in `app_config.json`), unified physical geometry + UI layout (`segments_full.json`, `segments_small.json`), and dynamic path resolution (`Configuration_manager.py`).
* `hardware/`: Physical abstractions (`Fake_leds.py`, `Rpi_NeoPixels.py`, `Udp_Sender.py`, `HardwareFactory.py`, `Fake_ESP32.py`).
* `connectors/`: Asynchronous integrations (`Connector.py` aiohttp server exposing `/ws`, `/api/topology`, `/api/configurations`, plus `Local_Microphone.py`).
* `wabb-interface/`: React-based remote control web interface.
* `data/`: Active profile preset stores: `configurations_full.json` (full profile) and `configurations_small.json` (small profile).

---

## 2. Core System Invariants

### 1. Hardware Profiles (`full` vs `small`)
* **`full` (Default)**: 1,304 LEDs across 11 segments on 2 channels (`segs_1`: 785 LEDs, `segs_2`: 519 LEDs). Uses `segments_full.json` and `configurations_full.json`.
* **`small`**: 249 LEDs across 3 segments on 1 channel (`segs_1`: `s1` 49, `s2` 108, `s3` 92). Uses `segments_small.json` and `configurations_small.json`.
* **Path Resolution**: Never hardcode file paths for segments or configurations. Always use `Configuration_manager.resolve_segments_file_path(infos)` and `resolve_configurations_file_path(infos)`.

### 2. PyGame Threading on Windows
PyGame is strictly bound to the **main thread** on Windows.
Whenever invoking `.show()` in `Mode_master.py`, always check `infos.get("onRaspberry")`:
* If `True` (Raspberry Pi): Use `loop.run_in_executor` to offload `neopixel.show()` and prevent `asyncio` loop stalls.
* If `False` (Windows Sim): Call `.show()` synchronously in the main thread to prevent "Not Responding" OS freezes.

### 3. Physical LED Wiring & Orientation
* **Full Profile**: Total LEDs: **1,304** across 11 segments.
* **Vertical Invariant**: Physical vertical LED strips (`v1`, `v2`, `v3`, `v4`) are wired **bottom-to-top**. In `Fake_leds.py`, their orientation is `"vertical_up"`, `y -= 2`, and `start_y` corresponds to their bottom-most coordinate.

### 4. Dev Server Port Collision Prevention
In local testing on Windows, `Main.py` sets `infos["startServer"] = False` by default to prevent socket collision crashes on `0.0.0.0:8080` during successive `Ctrl+C` restarts. Set `startServer: True` only when explicitly testing web connectors.

### 5. Code Style & Aliased Imports
Preserve existing aliased import conventions:
```python
import core.Mode_master as Mode_master
import hardware.Fake_leds as Fake_leds
```

---

## 3. Specialized Domain Skills Index

For specialized tasks, refer to or trigger the dedicated workspace skills:

| Domain | Skill Name | Location & Purpose |
|---|---|---|
| **Visual Modes** | `vialactee-mode-creator` | [`.agents/skills/vialactee-mode-creator/SKILL.md`](../vialactee-mode-creator/SKILL.md) — Vectorized rendering, `Mode` subclassing, `run()` method, and settings schemas. |
| **DSP & Beat Tracking** | `vialactee-dsp-engine` | [`.agents/skills/vialactee-dsp-engine/SKILL.md`](../vialactee-dsp-engine/SKILL.md) — Mel/chroma matrices, Anticipation Flywheel ("Oracle"), $T_{\text{speaker}}$ phase projection, and dynamic latency. |
| **Web UI & API** | `vialactee-web-connector` | [`.agents/skills/vialactee-web-connector/SKILL.md`](../vialactee-web-connector/SKILL.md) — REST endpoints, `/ws` WebSocket protocol, LIVE vs PERSIST topology actions. |
| **Hardware & Pi Deploy** | `vialactee-hardware-deploy` | [`.agents/skills/vialactee-hardware-deploy/SKILL.md`](../vialactee-hardware-deploy/SKILL.md) — Coordinate tables, GPIO NeoPixels, Pygame simulator, and Raspberry Pi deployment. |
