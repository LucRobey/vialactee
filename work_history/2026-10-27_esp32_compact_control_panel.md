# [2026-10-27] ESP32 Compact Control Panel (Segment Modes & Transition Tester)

> **Date:** 2026-10-27  
> **Session ID:** `0b44497b-a2c0-41d1-9570-d3c7c09b4100`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Enable a compact Pygame control panel (Segment Modes table + Transition Tester + optional Music Analyzer HUD) when running in `"esp32"` hardware mode without rendering simulated LEDs.  
> **Status:** COMPLETED  
> **Commits:** `09e4b64` (pushed: yes)  
> **Skills Used:** `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* When switching `"HARDWARE_MODE"` from `"simulation"` to `"esp32"` in [`config/app_config.json`](../config/app_config.json), the Pygame window was previously not launched, and [`Udp_Sender`](../hardware/Udp_Sender.py) transmitted port `9003` (`SEGMENT_METADATA_PORT`) telemetry packets to the remote ESP32 IP instead of `127.0.0.1`.
* The user requested keeping the Segment Modes table and Transition Tester controls on screen in `"esp32"` mode via a compact control window (without rendering the 1,304 simulated LEDs).

---

## 2. Changes Made

### Hardware & Visualizer (`hardware/`)
* **[MODIFY]** [`hardware/Udp_Sender.py`](../hardware/Udp_Sender.py):
  * Routed sideband UI metadata (`segment_mode`, `transition_state`, `analyzer_state` on `SEGMENT_METADATA_PORT = 9003`) to `("127.0.0.1", SEGMENT_METADATA_PORT)` while keeping pixel frames on `(self.ip, self.port)`. This feeds the local control panel in `"esp32"` mode and stops sending port `9003` JSON datagrams to the physical ESP32 over Wi-Fi.
* **[MODIFY]** [`hardware/VisualizerHud.py`](../hardware/VisualizerHud.py):
  * Added configurable `(px, py)` coordinates to `draw_segment_modes_table()`, `draw_transition_panel()`, and `draw_analyzer_hud()`, dynamically updating interactive button hitboxes (`_update_transition_rects(px, py)`) so mouse clicks work at any panel position.
* **[MODIFY]** [`hardware/Fake_leds.py`](../hardware/Fake_leds.py):
  * Added `hud_only` mode to `FakeLedsVisualizer` (`set_hud_only(True)` / `--hud-only`), opening a compact `732x304` window (`"Vialactée - ESP32 Control Panel"`) that renders only the `SEGMENT MODES` table and `TRANSITION TESTER` panel (and auto-expands to `732x661` if `--panel` / `show_music_analyser_panel` streams analyzer telemetry).
* **[MODIFY]** [`hardware/Fake_ESP32.py`](../hardware/Fake_ESP32.py):
  * Added `--hud-only` support in `main()`, skipping local pixel port bindings (`9001`/`9002`) in HUD-only mode while draining `PORT_METADATA` (`9003`) at 30 FPS for responsive UI controls.
* **[MODIFY]** [`hardware/HardwareFactory.py`](../hardware/HardwareFactory.py):
  * Updated `create_hardware()` in `"esp32"` mode to spawn `Fake_ESP32.py --hud-only` as a background process when running in a non-headless desktop environment.

### Tests & Documentation
* **[MODIFY]** [`tests/test_fake_esp32_and_fake_leds.py`](../tests/test_fake_esp32_and_fake_leds.py) & [`tests/test_udp_sender_throttling.py`](../tests/test_udp_sender_throttling.py):
  * Added unit tests verifying compact `hud_only` window dimensions, button rect alignment, `HardwareFactory` `--hud-only` process launch, and `Udp_Sender` localhost metadata routing when configured with a remote ESP32 IP.
* **[MODIFY]** [`docs/reference/configuration_schemas.md`](../docs/reference/configuration_schemas.md):
  * Documented the `"esp32"` compact control panel behavior in the Hardware Driver Modes table.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q tests/test_fake_esp32_and_fake_leds.py tests/test_udp_sender_throttling.py tests/governance/`
  * **Result**: `54 passed in 11.65s`.

---

## 4. Architecture Decisions & Trade-offs

* **Localhost Sideband Invariant**: Both `SEGMENT_METADATA_PORT` (`9003`) and `CONTROL_PORT` (`9004`) are strictly local IPC channels between `Main.py` and the Pygame UI. Always targeting `127.0.0.1` for port `9003` unifies `"simulation"` and `"esp32"` modes and avoids unnecessary Wi-Fi traffic to the microcontroller.
* **Headless Guard**: In `"esp32"` mode, `HardwareFactory` checks `SDL_VIDEODRIVER == "dummy"` and Linux `DISPLAY`/`WAYLAND_DISPLAY` before spawning `Fake_ESP32.py --hud-only`, preserving compatibility with headless Raspberry Pi `systemd` deployments.

---

## 5. Pitfalls & Lessons Learned

* `FakeLedsVisualizer` is instantiated at module import time in `hardware/Fake_leds.py`. Detecting `--hud-only` in `FakeLedsVisualizer.__new__` prevents briefly flashing a `1300x900` window before resizing to the compact layout.

---

## 6. Open Items & Next Steps

* None.
