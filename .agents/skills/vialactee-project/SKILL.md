---
name: vialactee-project
description: Central knowledge, architecture boundaries, and execution rules for the Vialactée interactive LED chandelier project. Use when modifying core orchestration, coordinating multiple domains, or onboarding to the codebase.
---

# Vialactée Project & Architecture Master Skill

Use this skill as the primary architectural authority for the Vialactée music-reactive LED chandelier repository. It defines global system invariants, threading models, and indexes the specialized domain skills.

---

## 1. Directory Structure

* `Main.py`: The asynchronous orchestration entry point.
* `core/`: The math and execution engine (`Mode_master.py`, `Transition_Director.py`, `Listener.py`, `AudioAnalyzer.py`, `AudioIngestion.py`, `Segment.py`).
* `modes/`: Visual light animation modes inheriting from `modes.Mode`.
* `config/`: Physical structure layouts (`segments.json`) and configuration managers.
* `hardware/`: Physical abstractions (`Fake_leds.py`, `Rpi_NeoPixels.py`, `Udp_Sender.py`, `HardwareFactory.py`).
* `connectors/`: Asynchronous integrations (`Connector.py` aiohttp server, `Local_Microphone.py`).
* `wabb-interface/`: React-based remote control web interface.
* `data/configurations.json`: Source of truth for saved playlists and segment configurations.

---

## 2. Core System Invariants

### 1. PyGame Threading on Windows
PyGame is strictly bound to the **main thread** on Windows.
Whenever invoking `.show()` in `Mode_master.py`, always check `infos.get("onRaspberry")`:
* If `True` (Raspberry Pi): Use `loop.run_in_executor` to offload `neopixel.show()` and prevent `asyncio` loop stalls.
* If `False` (Windows Sim): Call `.show()` synchronously in the main thread to prevent "Not Responding" OS freezes.

### 2. Physical LED Wiring
* Total LEDs: **1,304** across 11 segments.
* **Vertical Invariant**: Physical vertical LED strips (`v1`, `v2`, `v3`, `v4`) are wired **bottom-to-top**. In `Fake_leds.py`, their orientation is `"vertical_up"`, `y -= 2`, and `start_y` corresponds to their bottom-most coordinate.

### 3. Dev Server Port Collision Prevention
In local testing on Windows, `Main.py` sets `infos["startServer"] = False` by default to prevent socket collision crashes on `0.0.0.0:8080` during successive `Ctrl+C` restarts. Set `startServer: True` only when explicitly testing web connectors.

### 4. Code Style & Aliased Imports
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
