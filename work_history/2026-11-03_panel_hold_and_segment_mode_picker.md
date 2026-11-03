# [2026-11-03] Desktop Panel: HOLD / LIVE Switch & Per-Segment Mode Picker

> **Date:** 2026-11-03  
> **Session ID:** `3ac3a2b8-4033-427b-83e6-01194078eeef`  
> **Agent / Model:** Claude Sonnet 5.5 (High)  
> **Primary Goal:** From the pygame control panel opened by `Main.py` (not the web app), stop automatic transitions and choose each segment's mode, for a live presentation.  
> **Status:** COMPLETED  
> **Commits:** see `git log` (pushed: see final message)  
> **Skills Used:** `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* The web app already had HOLD / LIVE and a per-segment mode selector; the user wanted the same in the desktop panel (`Fake_ESP32 --hud-only` in `esp32` mode, the simulator window in `simulation` mode).
* The panel runs in a separate process and only knew segment modes and the transition state, so it needed a way to receive the available modes and to send commands back over the existing `CONTROL_PORT` (9004).

---

## 2. Changes Made

### Panel (pygame)
* **MODIFY** [`hardware/VisualizerHud.py`](../hardware/VisualizerHud.py): new **SHOW CONTROL** panel (HOLD / LIVE button, hotkey `H`); `<` `>` buttons on each row of SEGMENT MODES cycling that segment's modes (wraps; chains fast clicks via a 0.5 s optimistic cache); `handle_event(..., on_command)`.
* **MODIFY** [`hardware/Fake_leds.py`](../hardware/Fake_leds.py): `send_control_command` (in-process handler or UDP 9004), `update_mode_catalog`, window height accounts for the new panel; in-process `Fake_leds` wrapper forwards `is_locked`.
* **MODIFY** [`hardware/Fake_ESP32.py`](../hardware/Fake_ESP32.py): ingests `mode_catalog`; metadata recv buffer 4096 -> 65535.

### Main process
* **MODIFY** [`hardware/Udp_Sender.py`](../hardware/Udp_Sender.py): `set_control_handler(handler, mode_catalog)`; forwards non-`request_transition` control packets; `transition_state` now carries `is_locked`; `mode_catalog` sent at 1 Hz.
* **MODIFY** [`core/Mode_master.py`](../core/Mode_master.py): `handle_panel_command` (`set_locked`, `set_segment_mode`, validated against each segment's own modes) and `_panel_mode_catalog`, wired to `leds_list[0]`.
* **MODIFY** [`transitions/service.py`](../transitions/service.py) / [`api.py`](../transitions/api.py): `set_locked(True)` now also withdraws queued, not-yet-started transitions (pending downbeat transition, armed song/structure/pre-drop triggers, queued drop). Before, a transition queued just before HOLD still fired up to ~1 s later.

### Docs / tests
* `docs/architecture/hardware_abstraction.md`, `docs/reference/configuration_schemas.md`, `docs/contracts/transition_contract.md` updated.
* **NEW** `tests/test_panel_show_control.py` (HUD clicks/hotkey, UDP link, `Mode_master` commands) + one test in `tests/transitions/test_service.py`.

---

## 3. Verification & Testing

* `.venv\Scripts\python.exe -m pytest -q` -> `573 passed, 5 deselected` (before the final one-line hint-text edit; re-run before commit, see below).
* Rendered the panel off-screen (SDL dummy driver) in LIVE and HOLD states and checked the layout by eye (732x661 window with analyzer data).
* **Not tested:** a real run of `Main.py` with the ESP32 / microphone, i.e. clicking in the live window.

---

## 4. Architecture Decisions & Trade-offs

* Reused the existing `CONTROL_PORT` and `Udp_Sender` poll loop instead of a new channel; the handler is injected (`set_control_handler`) so `hardware/` never imports `core/`.
* HOLD and mode picking are separate controls (HOLD is not implied by picking a mode). In LIVE the panel says so, since the next automatic transition replaces manual picks.
* Per-segment mode lists are streamed (not read from `modes.json` in the panel) because vertical segments can differ from horizontal ones.
* The panel shows state only from the main process (no optimistic display), so a stale panel means the main process is not running.

---

## 5. Pitfalls & Lessons Learned

* Source files in `hardware/` and `core/` use CRLF; multi-line `edit_file` targets fail on them. Patch with a line-ending-aware script.
* The system `python` has no pytest; use `.venv\Scripts\python.exe`.

---

## 6. Open Items & Next Steps

* [ ] Live check on the real chandelier: HOLD, pick modes, go back to LIVE.
* [ ] The web app's HOLD switch benefits from the same queued-transition fix (shared `set_locked`).
