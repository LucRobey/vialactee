# [2026-11-02] Theatrical Transitions Overhaul & `transitions/catalog/` Refactoring

> **Date:** 2026-11-02  
> **Session ID:** `6ef0e229-c264-4ed8-a7da-e11fe87b0587`  
> **Agent / Model:** Gemini 4 Argon (High)  
> **Primary Goal:** Transform Vialactée's transition repertoire into 3-Act theatrical spectacles, add 6 new showstopper transitions (`supernova`, `shatter_ice`, `tesla_arc`, `fuse_detonate`, `liquid_geyser`, `pendulum_sweep`), iterate on 10 transitions based on live visual playtesting, and refactor all transition shaders into self-contained `1 transition = 1 file` modules under `transitions/catalog/` (modeled after `modes/`).  
> **Status:** COMPLETED  
> **Commits:** `7669a1d` `a0d9781` `2324f9f` `1c20e68` `80677b4` `0007394` (pushed: yes)  
> **Skills Used:** `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* On the 1,304-LED chandelier where active modes are already pulsing and strobing at 30 FPS, simple single-stage crossfades or 4%-thin wipes blend into the mode noise and go unnoticed.
* `explosion` stood out because it executes a **3-Act Theatrical Arc**: (I) inward horizon collapse creating pitch-black negative space, (II) brief compression blackout, and (III) radial shockwave unveiling the incoming mode at full brightness.
* Once transitions evolved into 60–90 line 3-Act shaders, packing all 29 transitions into 3 monolithic files (`engine.py`, `effects.py`, `spectacles.py`) pushed all three to ~460 lines (right against the AXIOM-07 500-line ceiling) and scattered each transition's metadata across 4 files. Refactoring into `transitions/catalog/` (`1 transition = 1 file`, like `modes/`) gives each transition its own self-contained 40–100 line module co-locating its `TransitionSpec` and pixel shader.

---

## 2. Changes Made

### Phase 1: Contract, Families & Generative Parameters (`7669a1d`)
* **[MODIFY]** [`transitions/api.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/api.py):
  * Added `"supernova"`, `"shatter_ice"`, `"tesla_arc"`, `"fuse_detonate"`, `"liquid_geyser"`, and `"pendulum_sweep"` to `AVAILABLE_TRANSITIONS`.
* **[MODIFY]** [`transitions/families.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/families.py):
  * Registered `TransitionFamily` contracts for all 6 new showstoppers and disabled `MODE_COOPERATIVE` on 3-Act blackout/kinetic showstoppers.
  * Added `spiral_arms` (`{2, 3}`), `trench_width` (`[0.12, 0.22]`), and `teeth_count` (`{3, 4, 5}`) to `DEFAULT_PARAMS`, `ACTIVE_PARAMS`, and `roll_transition_params()`.

### Phase 2: Upgraded Classics (`spiral`, `zipper_merge`, `collider`) & Dark-Trench Wipes (`a0d9781`)
* Upgraded `_apply_field_wipe` with a tapered pitch-black contrast trench (`trench_width`) ahead of a glowing shockwave crest (`beam_thickness`).
* Rebuilt `apply_spiral_transition` into a 3-Act Logarithmic Galaxy Vortex, `apply_zipper_merge` into a 3-Act Mechanical Interlock, and `apply_collider` into a 3-Act Hadron Particle Accelerator.

### Phase 3: New 3-Act Showstoppers (`2324f9f`)
* Implemented `apply_supernova`, `apply_shatter_ice`, `apply_tesla_arc`, `apply_fuse_detonate`, `apply_liquid_geyser`, and `apply_pendulum_sweep` (strictly $O(N)$ vectorized NumPy inside the sealed room).

### Phase 4: Durations, Auto Variety, Stagger Polish & Contract Docs (`1c20e68`)
* Increased showstopper and kinetic durations in `TRANSITION_TECHNIQUES` to `2.0 s – 3.4 s`.
* Added `roll_auto_transition_technique(context, staggered)` with anti-repeat memory across context-weighted pools.
* Preserved showcase techniques and durations across horizontal rings in `COHORT_COMPLEMENTARY` when `base_technique != "fade_in_out"`, normalized vertical pillar direction to `"UP"` in `BAY_WAVE_LR/RL`, and increased the default Simulator Transition Tester duration from `1.2 s` to `3.0 s`.

### Phase 5: Live Visual Playtest Refinements (`0007394`)
* **Tightened Central Epicenter (`supernova`, `spiral`, `explosion`)**: Clustered `_ARCHITECTURAL_EPICENTERS` and `DEFAULT_PARAMS` around the true visual center of the chandelier (`epicenter_x ∈ [0.55, 0.66]`, `epicenter_y ∈ [0.45, 0.55]`).
* **Smooth Tail Lock-In (`transformer_cut`, `shatter_ice`)**: Added a continuous smoothstep tail settle over the final 25–28% so `rgb_new` blooms in silkily without any hard step at $p=1.0$.
* **High-Voltage Yellow Capacitor Charge (`tesla_arc`)**: Kept Act III's bottom-to-top plasma surge intact while redesigning Act I (crackling electric yellow spark drain) and Act II (downward yellow-gold lightning bolts feeding a rising yellow-white capacitor pool at the floor).
* **Hydraulic Rebound & Rising Tide (`liquid_geyser`)**: Connected Act I's top-to-bottom meniscus drain directly to an elastic hydraulic bounce across the lower tiers in Act II that smoothly rises back up the pillars and horizontal bars in Act III.
* **Wide Perpendicular Wall (`box_wipe`)**: Boosted effective beam width (`max(0.30, beam_thickness * 2.2)`) so perpendicular bar crossings illuminate a bold segment.
* **Architectural Marble-Run Cascade (`gravity_drop`)**: Reworked `apply_gravity_drop` so luminous spheres roll left-to-right (`nx: 0 -> 1`) along the horizontal bars and plunge downward with gravity (`ny: 0 -> 1`) whenever they reach each vertical pillar (`v1`–`v4`).
* **3-Act Upgrades for `weird_glitch` & `global_change`**: Upgraded `apply_weird_glitch` into a 3-Act Cyberpunk Sector Corruption & Matrix Reboot, and `apply_colorful_glitch` (`global_change`) into a 3-Act Prism Rave Takeover.

### Phase 6: `1 Transition = 1 File` Refactoring (`transitions/catalog/`)
* **[NEW]** [`transitions/catalog/`](file:///c:/Users/lucro/Desktop/vialactee/transitions/catalog):
  * Created `_common.py` (acyclic DAG root holding `TransitionFamily`, `TransitionSpec`, `ACTIVE_PARAMS`, `ROOM_MAX_X/Y`, 1D caches, `norm_coords`, `central_epicenter`, and `apply_field_wipe`).
  * Created 24 self-contained transition files (`explosion.py`, `supernova.py`, `spiral.py`, `tesla_arc.py`, `box_wipe.py`, `weird_glitch.py`, `shatter_ice.py`, `liquid_geyser.py`, `pendulum_sweep.py`, `gravity_drop.py`, `vertical_wipe.py`, `horizontal_wipe.py`, `zipper_merge.py`, `collider.py`, `fuse_detonate.py`, `silk_wipe.py`, `iris.py`, `prism_sweep.py`, `ember_dissolve.py`, `luma_melt.py`, `breath_dip.py`, `dual_fade.py`, `global_change.py`, `flash_cut.py`, `staccato_shutter.py`, `transformer_cut.py`) and `__init__.py` (`CATALOG` & `TECHNIQUE_CONFIGS`).
* **[MODIFY]** [`transitions/families.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/families.py), [`transitions/manager.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/manager.py), & [`transitions/engine.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/engine.py):
  * Derived `TRANSITION_FAMILIES` and `TRANSITION_TECHNIQUES` directly from `transitions.catalog`.
  * Reduced `transitions/engine.py` from **465 lines down to 97 lines** while preserving `ROOM_MAX_X/Y`, `set_room_bounds()`, and the directly-tested `apply_*` functions.
  * Retired monolithic `transitions/effects.py` and `transitions/spectacles.py`.

### Phase 7: Post-Catalog Export & Dead-Code Cleanup (`transitions/`)
* **[MODIFY]** [`transitions/engine.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/engine.py) & [`transitions/catalog/__init__.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/catalog/__init__.py):
  * Removed obsolete `TRANSITION_DEFAULTS`, unused `logger`, and 17 unreferenced `apply_*` re-exports from `engine.py` and `catalog/__init__.py`.
* **[MODIFY]** [`transitions/policy.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/policy.py) & [`transitions/sandbox.py`](file:///c:/Users/lucro/Desktop/vialactee/transitions/sandbox.py):
  * Removed unused `random` and `Any` imports.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest tests/transitions/ tests/governance/ tests/test_room_bounds.py -q`
  * **Result**: All transition, room-bounds, and governance tests (`test_transition_isolation.py`, `test_axiom_07_code_governance.py`, `test_docs_parity.py`) passed.

---

## 4. Architecture Decisions & Trade-offs

* **Acyclic Catalog DAG (`_common.py` $\to$ `catalog/*.py` $\to$ `catalog/__init__.py` $\to$ `families.py` / `manager.py` / `engine.py`)**: Defining `TransitionFamily` and `TransitionSpec` in `_common.py` prevents circular imports while allowing each transition file to declare its own families, duration, and handler in one place.

---

## 5. Pitfalls & Lessons Learned

* **Dual Room-Bounds Synchronization**: Because `tests/test_room_bounds.py` inspects `TE.ROOM_MAX_X` / `TE.ROOM_MAX_Y` on `transitions.engine` after calling `TE.set_room_bounds()`, `engine.set_room_bounds()` updates both its module globals and `transitions.catalog._common`.
* **4 Dispatch Signatures (`TransitionSpec.kind`)**: Preserving `"strip_1d"`, `"spatial_spectacle"` (runs with `coords=None` via 1D fallback), `"spatial_wipe"` (forwards `beam_thickness`, falls back to `apply_dual_fade` when `coords=None`), and `"spatial_room"` keeps 100% compatibility with existing engine unit tests.

---

## 6. Open Items & Next Steps

* [x] Refactor transitions into `transitions/catalog/` (`1 transition = 1 file`).
* [ ] Optional future enhancement: emit a `PaletteRequest` on Act II/III climax of `supernova` / `explosion` so the room's colour mood snaps on the shockwave.
