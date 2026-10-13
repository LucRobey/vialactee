# [2026-10-13] Transitions Sector Cleanup, Adapter Shim Removal & All-Blocked Desync Fix

> **Date:** 2026-10-13  
> **Session ID:** `6aa3e7c5-933e-4a9c-b7aa-a0628ccdbe4a`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Execute the transitions sector cleanup plan: fix the all-blocked director desync, delete dead director state (`dt` passed directly), remove the `_Host`/`_SegmentView`/`_MusicView` adapter shim, deduplicate engine/stagger helpers, and sync `docs/reference/transition_contract.md`.  
> **Status:** COMPLETED

---

## 1. Context & Motivation

Following the sealed-room extraction of `transitions/` behind `transitions/api.py`, a code review identified five concrete cleanups and bug fixes inside the transitions sector:

1. **All-blocked segment desync bug**: `LocalTransitionManager._execute_transition` previously called `Transition_Director.start_transition(...)` even when every segment in `allocation` was blocked (`is_blocked=True`) and zero `SegmentOrder`s were emitted. Because `DefaultTransitionService.update` returns `()` when no orders are emitted, `Mode_master` never calls `ack_orders(...)`, stranding `Transition_Director` in `TRANSITION_DUAL` for its full duration.
2. **Dead director state & first-frame `dt` hack**: `Transition_Director` carried dead silence/standby fields (`silence_threshold`, `silence_duration_trigger`, `silence_start_time`, `is_in_standby`), an unused `transition_step` counter, dead geometry lists (`verticals`, `horizontals`, `all_segments`, `segments_path`, `_load_segments`), and `last_update_time` (which silently ignored the real `dt` on the first `update()` call in favor of `1/60`).
3. **Redundant `_Host` / `_SegmentView` / `_MusicView` adapter shim**: `transitions/service.py` maintained three private adapter classes translating `InstallationSnapshot` and `MusicSnapshot` into a fake `Mode_master` duck-type for `LocalTransitionManager`, which in turn mutated dummy `activ_configuration` and `_state_dirty` attributes.
4. **Dormant feature notes & helper deduplication**: `transitions/stagger.py` and `transitions/engine.py` contained spatial wipe and cohort stagger routines not yet wired into automatic selection, plus repeated per-pixel wipe threshold application in `engine.py` and 4 nearly identical cohort step-offset loops in `stagger.py`.
5. **Documentation parity**: `docs/reference/transition_contract.md` listed `[GAP]` entries for the items above that needed to be updated to reflect the resolved state.

---

## 2. Changes Made

### Transitions Sector (`transitions/`)
* **[MODIFY]** [`transitions/director.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/director.py):
  * Removed dead attributes (`silence_threshold`, `silence_duration_trigger`, `silence_start_time`, `is_in_standby`, `transition_step`, `verticals`, `horizontals`, `all_segments`, `segments_path`, `last_update_time`) and deleted `_load_segments()`.
  * Changed `update(self, dt: float, music: Optional[Any] = None) -> bool` to accept `dt` directly instead of computing `current_time - self.last_update_time` with a hardcoded `1.0 / 60.0` first-tick fallback.
  * Preserved `self.is_pending` when an active transition completes so a transition queued during `TRANSITION_DUAL` does not lose its pending state or trigger reason.
* **[MODIFY]** [`transitions/manager.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/manager.py):
  * Replaced the `mode_master` host parameter with `(director, segments, music)` operating directly on `SegmentDescriptor` and `MusicSnapshot`.
  * Added `set_installation(segments)`, `set_active_mode(segment_name, mode_name)`, and `pop_orders() -> Tuple[SegmentOrder, ...]`.
  * Removed dummy writes to `segment.activ_configuration` and `self.host._state_dirty`.
  * Fixed `_execute_transition` so `self.director.start_transition(...)` is only called when `emitted > 0`; when 0 orders are emitted (empty allocation or all segments blocked), `self.director.is_pending` is reset to `False` so the director stays in `PASSATION`.
  * Cleared `self._pending_transition = None` on immediate (`quantize_downbeat=False`) transitions and cleared `self._orders` at the start of `_execute_transition` to prevent stale pending transitions or duplicate per-segment orders.
* **[MODIFY]** [`transitions/service.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/service.py):
  * Deleted `_MusicView`, `_SegmentView`, and `_Host` (~55 lines of adapter shim).
  * Wired `DefaultTransitionService` directly to `Transition_Director` and `LocalTransitionManager`, forwarding `dt` directly into `self._director.update(dt, music)`, executing `request_drop` inside `update()` after `director.update(dt, music)` so `progress` starts at `0.0` on the emission frame, and draining orders via `self._manager.pop_orders()`.
* **[MODIFY]** [`transitions/engine.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/engine.py):
  * Added `# Note: ... not wired into automatic selection today` module docstring note for spatial/glitch effects (`horizontal_wipe`, `box_wipe`, `spiral`, `gravity_drop`, `colorful_glitch`, `weird_glitch`).
  * Extracted `_apply_field_wipe(rgb_list_old, rgb_list_new, field, progress, beam_thickness=0.04)` and refactored `apply_horizontal_wipe`, `apply_vertical_wipe`, `apply_box_wipe`, `apply_spiral_transition`, and PNG fallback to delegate to it.
* **[MODIFY]** [`transitions/stagger.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/stagger.py):
  * Added `# Note: not wired into automatic transitions yet` module docstring note.
  * Extracted `_step_distance(idx, total, pattern)` to replace the 4 duplicated cohort loop blocks in `generate_staggered_configs`.

### Documentation & Tests
* **[MODIFY]** [`docs/reference/transition_contract.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/transition_contract.md):
  * Updated Part B (`Transition_Director`, `LocalTransitionManager`, `DefaultTransitionService`) and §6 `[GAP]` table to reflect the removed dead state, removed `_Host` shim, direct `dt` passing, and the all-blocked segment guard.
* **[MODIFY]** [`tests/transitions/test_transition_director.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/transitions/test_transition_director.py):
  * Updated `director.update(...)` calls to pass `dt` directly; removed assertions on deleted attributes (`verticals`, `horizontals`, `all_segments`, `is_in_standby`); added `test_first_update_uses_exact_dt_without_hardcoded_frame_step`.
* **[MODIFY]** [`tests/transitions/test_service.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/transitions/test_service.py):
  * Added `test_all_blocked_segments_do_not_desync_director_into_transition_dual`, `test_segments_blocked_during_downbeat_wait_window_do_not_desync_director`, `test_immediate_drop_supersedes_pending_downbeat_transition`, `test_duplicate_request_drop_emits_one_order_per_segment`, and `test_request_next_queued_during_active_transition_preserves_reason`.
* **[MODIFY]** [`tests/test_mood_and_transitions.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/test_mood_and_transitions.py):
  * Updated `TestLocalTransitionManager` and `TestRobustnessAndEdgeCases` to construct `LocalTransitionManager(director=..., segments=..., music=...)` with `SegmentDescriptor`s and verify emitted `SegmentOrder`s via `pop_orders()`.
  * Added `test_all_blocked_segments_do_not_start_director_transition` and `test_immediate_schedule_transition_clears_pending_and_replaces_undrained_orders`.
* **[MODIFY]** [`tests/test_local_audio_file.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tests/test_local_audio_file.py):
  * Updated `test_startup_transition_stability_and_ring_buffer_cleanliness` to pass `dt` instead of cumulative `current_time` to `director.update(dt, music)`.

---

## 3. Verification & Testing

* **Command**: `python -m pytest tests/governance/ tests/transitions/ tests/test_mood_and_transitions.py tests/test_transition_bridge.py tests/test_local_audio_file.py -q`
  * **Result**: `152 passed, 34 subtests passed`
* **Command**: `python -m transitions.sandbox --seconds 30 --interval 5 --seed 1`
  * **Result**: Exited 0 (`3 transitions in 30s`, deterministic orders and completions across all 16 segments).

---

## 4. Architecture Decisions & Trade-offs

* **Resetting `director.is_pending` when 0 orders are emitted**: When `director.update()` triggers a transition (or `request_next` / `request_drop` sets `is_pending = True`), skipping `director.start_transition()` when all segments are blocked would leave `director.is_pending = True` indefinitely unless explicitly cleared. Resetting `self.director.is_pending = False` in `_execute_transition` when `emitted == 0` ensures the director cleanly returns to `PASSATION` and can trigger normally once segments are unblocked.
* **Retaining optional `segments_path` in `DefaultTransitionService.__init__`**: Kept as an unused optional keyword argument on `DefaultTransitionService.__init__` so `create_transition_service(segments_path=...)` in `transitions/api.py` and `core/Mode_master.py` remain 100% source-compatible without touching outside-the-wall callers.

---

## 5. Pitfalls & Lessons Learned

* **AXIOM-07 500-line cap on `transitions/manager.py`**: Adding `SegmentOrder` construction and helper methods (`set_installation`, `set_active_mode`, `pop_orders`) briefly pushed `transitions/manager.py` to 530 lines, which was caught by `TestAxiom07CodeGovernance.test_file_line_counts_and_ratchet`. Tightening verbose docstrings and vertical formatting brought `transitions/manager.py` down to 480 lines.

---

## 6. Open Items & Next Steps

* [ ] Decide when to wire `transitions/stagger.py` (`staggered=True`) into automatic transitions in `DefaultTransitionService.update`.
* [ ] Decide whether additional spatial/glitch effects in `transitions/engine.py` (`horizontal_wipe`, `box_wipe`, `spiral`, `gravity_drop`, `colorful_glitch`, `weird_glitch`) should be added to `TRANSITION_TECHNIQUES` in `transitions/manager.py` or retired.
