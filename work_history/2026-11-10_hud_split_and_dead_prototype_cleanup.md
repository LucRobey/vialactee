# [2026-11-10] HUD split, panel-command extraction, and dead Global Mode prototype cleanup

> **Date:** 2026-11-10  
> **Session ID:** `review-followup-115558e`  
> **Agent / Model:** Claude Opus 5.5  
> **Primary Goal:** Undo the AXIOM-07 (500-line cap) workarounds introduced in `115558e` and remove the 5 unused Global Mode prototypes.  
> **Status:** COMPLETED  
> **Commits:** `6b8ce37` (pushed: no)  
> **Skills Used:** none  
> **Skill Friction:** none

---

## 1. Context & Motivation

* A review of the last pushes (`115558e`, `03855c6`, `60141a5`, `6802657`) found:
  * `hardware/VisualizerHud.py` went from 1 to 51 lines joining several statements with `;`, ending at 497 lines. Written normally it was well past the 500-line cap.
  * `core/Segment.py` stayed at exactly 475 lines by cramming three statements onto one line, and `core/CommandRouter.py` gained a one-line `for` with an inline ternary.
  * The desktop-panel command logic (including mood commands) was moved from `Mode_master` into `core/TransitionBridge.py`, which is the transition-sector glue. That looked like it was done to save lines, not because it belongs there.
  * 5 prototype modes (~1,760 lines) were committed although `config/modes.json` no longer references them.
* The user asked to fix these two items. The separate web-UI bug (see Open Items) was left out on purpose.

---

## 2. Changes Made

### Simulator HUD (`hardware/`)
* **[NEW]** [`hardware/AnalyzerHud.py`](../hardware/AnalyzerHud.py): `AnalyzerHud` base class with the Music Analyzer HUD, the font and text caches, and the drawing helpers (`_draw_button`, `_draw_box`, `_blit_clipped`, `_hud_*`). It also adds a `_build_panel_surfaces()` hook that subclasses use to pre-render their own surfaces.
* **[NEW]** [`hardware/ShowControlPanel.py`](../hardware/ShowControlPanel.py): `ShowControlPanel(AnalyzerHud)` holds the SHOW CONTROL panel (HOLD/LIVE, scope, Global Mode and Mood pickers, AUTO toggle) and the SEGMENT MODES table with its pickers. It owns `CONTROL_PANEL_H`, `_load_global_mode_names` and `_load_mood_catalog`. The old 80-line `draw_control_panel` is split into `_sync_control_state`, `_draw_scope_rows` and `_draw_mood_rows`.
* **[MODIFY]** [`hardware/VisualizerHud.py`](../hardware/VisualizerHud.py): `VisualizerHud(ShowControlPanel)` now only holds the Transition Tester and the event routing (`_handle_click`, `_handle_key`). It re-exports `CONTROL_PANEL_H`, so `Fake_leds.py` is unchanged. Size went from 497 to 158 lines, and no line joins statements with `;` any more.
* The public attribute surface is unchanged, so existing tests and `Fake_leds` work as before.

### Core
* **[NEW]** [`core/PanelCommands.py`](../core/PanelCommands.py): `apply_panel_command` and `sync_mode_scope` moved here from `TransitionBridge.py`. The `if` chain became one handler per command type plus a dispatch table, with the same behaviour (`_state_dirty` is set only when a command is applied).
* **[MODIFY]** [`core/TransitionBridge.py`](../core/TransitionBridge.py): back to transition-sector glue only (305 → 190 lines). It no longer imports `mood.api`.
* **[MODIFY]** [`core/Mode_master.py`](../core/Mode_master.py): `handle_panel_command` now delegates to `PanelCommands`.
* **[MODIFY]** [`core/Segment.py`](../core/Segment.py): the mode-instantiation and `bind_segment_geometry` call is written on separate lines again (475 → 479 lines).
* **[MODIFY]** [`core/CommandRouter.py`](../core/CommandRouter.py): the global-mode fan-out in `select_segment_mode` is written out over several lines. Behaviour is unchanged.

### Dead code
* **[DELETE]** `modes/Architectural_drum_mode.py`, `modes/Synaptic_grid_mode.py`, `modes/Tilt_tank_mode.py`, `modes/Prism_lighthouse_mode.py`, `modes/Attractor_orb_mode.py`: never referenced by config, tests or code. They can be recovered with `git show 115558e:modes/<Name>_mode.py`.
* **[MODIFY]** [`docs/research/2026-11-09_global_audio_modes_research_and_design.md`](../docs/research/2026-11-09_global_audio_modes_research_and_design.md): the prototype list now uses module names instead of paths, plus a note saying where to recover the files (`test_docs_parity` rejects backticked paths that don't exist).
* **[MODIFY]** [`docs/contracts/transition_contract.md`](../docs/contracts/transition_contract.md): now points to `ShowControlPanel.py` for the SEGMENT MODES table.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `600 passed, 5 deselected, 187 subtests passed in 50.15s`
* **Headless smoke render** (`SDL_VIDEODRIVER=dummy`): drew all four panels in both global and local scope, with and without a crossfade or transition running. Fed the H, G, M, A, T and `[` hotkeys and a SEGMENT MODES `>` click. Each one emitted the expected command (`set_locked`, `set_mode_scope`, `set_mood`, `set_mood_auto`, send, `set_segment_mode`).
* **Not done:** a visual check in the real Pygame window (`Main.py --panel`).

---

## 4. Architecture Decisions & Trade-offs

* **Inheritance chain instead of composition for the HUD:** tests and `Fake_leds` reach about 40 HUD attributes directly (`hud._rect_hold`, `hud.mood_palettes`, …). A chain `AnalyzerHud → ShowControlPanel → VisualizerHud` keeps that surface identical while giving each file one job.
* **`sync_mode_scope` lives in `PanelCommands`:** for now only panel commands switch scope. It stays public so the web route (`CommandRouter`) can call it when the open item below is fixed.

---

## 5. Pitfalls & Lessons Learned

* The AXIOM-07 test only counts lines, so joining statements with `;` gets past it. When a file nears 500 lines, split it by responsibility instead.

---

## 6. Open Items & Next Steps

* [x] **Fixed later the same day in [`2026-11-10_web_mode_scope_sync_fix.md`](2026-11-10_web_mode_scope_sync_fix.md).** Bug (not fixed here): `CommandRouter._handle_topology_select_segment_mode` (web UI) swaps every segment to a Global Mode but never calls `PanelCommands.sync_mode_scope`. As a result the transition sector stays in per-segment mode and breaks the unison at the next automatic transition. The reverse case (picking a local mode while global is active) never switches back. The fix is probably to route it through `PanelCommands._set_segment_mode`. A test for the web path is needed too.
* [ ] `modes/Mode.py` (498 lines) and `core/Segment.py` (479 lines) are close to the 500-line cap.
