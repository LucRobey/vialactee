# 2026-11-10 Web Mode Selection: Transition Scope Sync Fix

> **Date:** 2026-11-10  
> **Session ID:** `18db9bd6-5abd-4710-b19f-969e52258417`  
> **Agent / Model:** Claude Fable 5.2  
> **Primary Goal:** Fix the web UI bug left open by the HUD-split session: picking a mode from the web UI did not switch the transition sector's scope.  
> **Status:** COMPLETED  
> **Commits:** none yet (pushed: no)  
> **Skills Used:** none  
> **Skill Friction:** none

---

## 1. Context & Motivation

* Open item from [`2026-11-10_hud_split_and_dead_prototype_cleanup.md`](2026-11-10_hud_split_and_dead_prototype_cleanup.md): `CommandRouter._handle_topology_select_segment_mode` swapped every segment to a Global Mode but never called `PanelCommands.sync_mode_scope`.
* Reproduced before fixing: after a web pick of "Stalagmites", `_use_global_modes` stayed unset and the next automatic transition ordered three different local modes (Bary Rainbow, Metronome, Hyper Strobe) across the segments.
* The reverse case was also broken: picking a local mode from the web UI while in global scope left the sector in global scope.

---

## 2. Changes Made

### Core
* **[MODIFY]** [`core/PanelCommands.py`](../core/PanelCommands.py): the body of `_set_segment_mode` is now the public `select_segment_mode(mode_master, segment_ref, mode_name)`. The panel handler calls it.
* **[MODIFY]** [`core/CommandRouter.py`](../core/CommandRouter.py): `topology/select_segment_mode` calls `PanelCommands.select_segment_mode` instead of swapping segments itself. An unknown mode now returns `{"applied": false, "reason": "unknown_mode"}`; before, it logged a warning and returned `applied: true` without changing anything.

### Tests and docs
* **[MODIFY]** [`tests/test_global_modes.py`](../tests/test_global_modes.py): new `test_web_mode_selection_keeps_the_transition_scope_in_sync`. It asks the transition sector for its next automatic transition and checks the ordered modes: one shared Global Mode after a web global pick, only local modes after a web local pick, and no change on an unknown mode.
* **[MODIFY]** [`docs/architecture/api_and_wire_protocol.md`](../docs/architecture/api_and_wire_protocol.md): the instruction's row describes the new path and the `unknown_mode` reason.

---

## 3. Verification & Testing

* The new test failed before the fix (`the web pick left the sector in per-segment scope`) and passes after it.
* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `629 passed, 5 deselected, 275 subtests passed in 50.48s`
* **Not done:** a check through the real web UI (React app + WebSocket). The test drives `Mode_master.process_instruction` directly with the same instruction the UI sends.

---

## 4. Architecture Decisions & Trade-offs

* **One function for both entry points** rather than adding a `sync_mode_scope` call to the web handler. The two paths had already drifted once; sharing the code is what stops it happening again. This is the fix the HUD-split log suggested.
* **Mixed state is kept as the panel defines it.** Picking a local mode on one segment while the others run a Global Mode leaves those others on the Global Mode until the next transition, which then recasts everything locally. `test_mixed_global_and_per_segment_switching_in_mode_master` already pins that for the panel; the web path now behaves the same.

---

## 5. Pitfalls & Lessons Learned

* This fix edits `core/PanelCommands.py` and `core/CommandRouter.py`, which carry the HUD-split session's uncommitted changes (`PanelCommands.py` is untracked). It cannot be committed on its own: it has to go in with, or after, that work.

---

## 6. Open Items & Next Steps

* [ ] Commit the HUD-split work and this fix.
* [ ] `wabb-interface/src/components/pages/TopologyEditor.tsx` was not checked for how it reacts to `applied: false` on an unknown mode.
