# 2026-10-19 Modes Audit, Dead-Mode Removal, Shared Helpers & Extending_waves Polish

> **Date:** 2026-10-19  
> **Session ID:** `374041df-8a1c-4964-b609-2b798c97295d`  
> **Agent / Model:** Antigravity (Claude Sonnet 5.5) + 3 read-only audit subagents  
> **Primary Goal:** Start the modes-quality effort: audit all modes, remove dead ones, add shared authoring helpers, and begin polishing the owner's favourites (Extending_waves, Shining_stars, Rainbow).  
> **Status:** IN PROGRESS (Shining_stars, Rainbow and the merge/rework batches remain)  
> **Commits:** `6f330ee`  
> **Skills Used:** `vialactee-project`, `vialactee-mode-creator`  
> **Skill Friction:** none

---

## 1. Context & Motivation

The new sound analysis / musical-context architecture is well used by the transitions; the owner wanted the same quality for the modes ("many modes look boring and random"; favourites: `Extending_waves`, `Shining_stars`, `Rainbow`). Decisions taken with the owner: remove `Alcool_randomer` and `Matrix_rain`, keep `Bary_rainbow` as its own mode, accept merging/retiring near-duplicate modes in later batches.

A static audit (three subagents, same rubric) produced a taste profile of the favourites (memory/trails, event-driven layered objects, spatial meaning, dark negative space, scene-aware choreography, soft sub-pixel profiles) and a per-mode verdict table. The audit is **inferred from code only**; nothing was judged on real LEDs.

---

## 2. Changes Made

### Removed modes
* **[DELETE]** `modes/Alcool_randomer.py` and **[DELETE]** `modes/Matrix_rain_mode.py`, plus their entries in `config/modes.json`, `transitions/mode_dna.py`, `modes/README.md`, `modes/modes_description.md`, `docs/reference/modes_catalog.md`, the web CSS animations, tests and mode counts (22 -> 21).
* **[MODIFY]** `wabb-interface/src/constants/topologyData.ts`: default mode of segment `v3` is now `Power Bar` (was `Matrix Rain`).
* Historical records (`work_history/`, `docs/archive/`) intentionally untouched.

### Shared helpers (Phase 1)
* **[MODIFY]** [`modes/Mode.py`](../modes/Mode.py): added `drop_hit` (1-frame trigger) / `drop_decay` (1->0 envelope), `dt` / `fps_ratio` / `alpha(rate_hz)`, `palette_lut` + `palette_sample`, luminance-safe `highlight_color`, confidence-blended `beat_pulse`, `segment_phase_offset`. `smooth_vectorized` / `smooth_segment_vectorized` no longer allocate per call (about 10-15 % faster on the benchmarked modes; numerically identical to the legacy two-step truncating blend).
* **[MODIFY]** [`modes/MODE_RULES.md`](../modes/MODE_RULES.md): new section 6 documenting the helpers, "never cache `rgb_list` views" and "settings must be read".
* **[MODIFY]** [`modes/Coloured_middle_wave_mode.py`](../modes/Coloured_middle_wave_mode.py): fixed a real bug: it cached views of `self.rgb_list`, so during transitions (`Mode.render(buffer=...)` redirect) it drew into the outgoing buffer.
* **[NEW]** [`tests/test_mode_helpers.py`](../tests/test_mode_helpers.py): helpers, blender equivalence vs the legacy implementation, the transition-buffer fix, and a dead-settings **ratchet** (`KNOWN_DEAD`: Beat_runner `base_hue`, Impact_shockwave `color_saturation`/`enable_ghost_ripples`, Rhythm_breather `base_hue`/`drift_speed`).

### Extending_waves (favourite 1/3): polish tried, rejected, reverted
* First attempt (commit `0ae6968`): drop = one wave + echoes, ambient afterglow, soft fallback wave, optional tail. **The owner rejected it ("very bad")**, so the mode was restored byte-for-byte to its pre-polish version (the version the owner loves) and only one change was made on request.
* **[MODIFY]** [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py): a wave is now injected on **every rhythmic tempo tick** (flywheel `listener.is_beat`, which fires once per beat period at speaker time even when no acoustic transient backs it), not only on verified real beats. `is_real_beat` stays in the trigger union. Everything else is the original: centre-out symmetry, additive overlap, 8 waves, BPM speed, BUILDUP implode, drop explode (including the original per-frame drop spawning, which was *not* changed).
* **[MODIFY]** [`tests/test_extending_waves.py`](../tests/test_extending_waves.py): tempo-tick tests (unverified tick spawns, no tick = no wave, one wave per tick over a bar, debounce, buildup implode, symmetry).
* Lesson: do not restyle the owner's favourites on the strength of a static audit; change only what is asked, review in `mode_studio` first.
### Extending_waves: drop-impact behaviour removed (owner request)
* **[MODIFY]** [`modes/Extending_waves_mode.py`](../modes/Extending_waves_mode.py): removed the whole drop-impact behaviour: the per-frame wave flood during the 1.5 s dwell, the 2x speed boost, the full-amplitude `mood[3]` explosion wave, and the `is_drop`/`drop_prog` variables. A drop is now just ordinary tempo-tick waves. The BUILDUP inward waves are kept (not part of the request).
* **[MODIFY/NEW]** `tests/test_extending_waves.py` (drop without tick spawns nothing; drop with tick = one ordinary wave in the normal palette) and the explosion assertion in `tests/test_all_modes_musical_context.py`.
* Scope: only `Extending_waves` was changed. Other modes still have their own drop behaviour (the copy-pasted `is_drop = ... or scene == "DROP_IMPACT"` pattern).
### mode_studio dropped beat ticks (found while verifying the tempo-tick change)
* **Symptom (owner):** the Oracle flywheel dial was perfectly aligned with the rhythm but Extending_waves did not spawn a wave on every tick.
* **Root cause:** `is_beat` / `is_real_beat` are one-frame flags, cleared at the start of every `listener.update()`. `tools/mode_studio.py` catches up with up to 6 analyzer steps per screen frame (`advance_ingest_frame`) but rendered the mode once afterwards, so ticks set in earlier sub-steps were erased before the mode saw them. The HUD dial reads the continuous `beat_phase`, so it kept looking aligned. Measured headless with a simulated 60 Hz clock over 54 ticks: the mode saw 100 % with 1 step/render, 48 % with 2, 44 % with 3, 20 % with 6.
* **[MODIFY]** [`tools/mode_studio.py`](../tools/mode_studio.py): the main loop now passes `on_frame_step=self.mode_mgr.render`, so the mode renders after every analyzer step (the hook's documented purpose) and advances in lock-step with audio time; paused/idle still renders once per frame.
* **[NEW]** [`tests/test_studio_ingest_contract.py`](../tests/test_studio_ingest_contract.py).
* **Production is not affected:** `Mode_master.update()` calls `listener.update()` once and then updates the segments once per frame.
* **Side finding (not changed):** `Listener.update` uses wall-clock `time.time()` for `current_time` even when `fixed_dt` is given, and the analyzer's beat debounce uses it, so headless fast-forward harnesses must simulate the clock.
### Tests hardened
* `test_axiom_02_zero_dynamic_heap_allocations` (`tests/test_all_modes_musical_context.py`): untraced 100-frame settle loop per scene, `gc.collect()` before measuring, one re-measure before failing, and a **512-byte** noise floor. Evidence: the flagged blocks were two ~52-byte allocations on separate stacks (allocator/NumPy bookkeeping, appeared only when run together with other test modules); a mode that retains ONE float per frame produces ~4000 bytes and is still caught.
* `Coloured_middle_wave_mode`: rgb_list views are now cached keyed by buffer identity (no per-frame view allocation, still correct when `Mode.render(buffer=...)` redirects the buffer).
* `tests/governance/test_docs_parity.py` and mode-count assertions updated to 21.
---

## 3. Verification & Testing

* **Command**: `python -m pytest -q` (final run, nothing else running)
  * **Result**: `417 passed, 1 failed, 5 deselected` (final run). The one failure, `tests/test_transition_bridge.py::TestApplyOrders::test_accepts_started_transitions_and_refuses_the_rest`, **fails identically on a clean `HEAD`** (expects `change_mode(..., {...})` without the newer `'mode_handshake': False` key). Unrelated to modes; left untouched.
* **Note on timing tests**: `test_axiom_01_frame_execution_time` and the analyzer CPU-budget tests failed once when a benchmark/suite overlapped (machine load) and passed on isolated reruns. A before/after benchmark (80 LEDs, best of 7x300) showed every mode equal or faster than `HEAD`.
* **Hardware / Simulator**: not run. Visual quality of the Extending_waves changes has **not** been reviewed in `mode_studio` yet.

---

## 4. Open Follow-ups

1. **Owner review in `tools/mode_studio.py`** of the tempo-tick Extending_waves before touching Shining_stars and Rainbow. Open question: the original drop behaviour spawns a wave every frame of the 1.5 s drop dwell; owner has not asked to change it.
2. Shining_stars: drop as starburst (not 1.5 s solid fill), soft 3-LED stars with white core, distinct colour for all 8 bands (`mood[i % 4]` repeats), remove the 1100-iteration import-time warmup.
3. Rainbow: confidence-blend the phase pulse, drift in all scenes (no snap leaving CHILL), BUILDUP compression, drop white sweep, optional palette gradient.
4. Merges/reworks agreed in principle: Impact_shockwave -> Extending_waves; Static_wave/Middle_bar/Opposite_sides -> "Core bar"; Magnetic_ball/Flying_ball/Chromatic_chaser -> "Comet"; rework Plasma_fire, Synesthesia; retire Metronome, PSG, Rhythm_breather (its logic is already `Mode.beat_pulse`). **Bary_rainbow stays as its own mode.**
5. Not yet done from the helper plan: shared Gaussian/wave-emitter helper (do it with the Impact_shockwave merge), float accumulation buffer for smooth dim trails (blenders still truncate into the int buffer), HSV hue LUT (`fromHSV_toRGB_vectorized` allocates ~15-25 temporaries per call), per-mode adoption of `drop_hit`/`highlight_color` (the copy-pasted `is_drop = ... or scene == "DROP_IMPACT"` still exists in most modes), `modes_description.md` entry for the new Extending_waves behaviour and settings.
6. `IDEAS.md` (user scratchpad) not touched; bespoke per-mode transitions (e.g. white-stacking Extending_waves exit) remain Phase 3.
