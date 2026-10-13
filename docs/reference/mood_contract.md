# Mood Sector Contract

Sibling of [`transition_contract.md`](transition_contract.md). The mood sector lives in `mood/` and is a **sealed room**: it talks to the rest of the project only through the doors below, defined in code in [`mood/api.py`](../../mood/api.py).

## Part A: The Doors (authoritative)

**Wall rules** (enforced by `tests/governance/test_mood_isolation.py`)
1. Nothing in `mood/` imports project code (`core/`, `modes/`, `connectors/`, `hardware/`, `transitions/`, ...). Only the standard library and numpy.
2. Nothing outside `mood/` imports from it except `mood.api`.
3. `api.py` uses only the standard library and numpy.
4. The front door is **synchronous**.
5. Sibling sectors never import each other: `core/` glue translates (for example `PaletteRequest` from `transitions.api` becomes `MoodService.request_palette`).

| # | Door | Dir | Shape (in `api.py`) | Notes |
| :-: | :--- | :-: | :--- | :--- |
| 1 | Clock + scene | in | `update(dt, scene)` | Called every frame by `Mode_master`. `scene` is a plain string (e.g. `"BUILDUP"`), optional. |
| 2 | Requests | in | `request_palette(name, duration)`, `next_palette()`, `set_auto_scene(enabled)` | UI selection (`select_mood`) and transition palette requests arrive here. Unknown names return `False`. |
| 3 | Colours | out | `colors()` | One **read-only** `(4, 3)` `int32` array `[primary, secondary, accent, background]`. Always the same object, updated in place: zero allocation. |
| 4 | Status | out | `get_status()` -> `MoodStatus` | Palette, target, progress, transitioning, available palettes, auto-scene flag. Feeds `activeMood` / `availableMoods` in the UI snapshot. |

**Ownership.** The room owns: the curated palettes, the cosine crossfade and the scene-to-palette rules. The outside owns: when to call it, the UI, and what modes do with the colours. Modes never import `mood`: `Mode_master` binds the live view once with `Mode.bind_mood_colors(mood.colors())` (the same class-level pattern as `Mode.listener`), and modes read `self.mood_colors`. `Mode.reset_mood_colors()` restores a static fallback palette for tests.

**Change policy.** Inside the room anything may change freely. Changing a door means editing `api.py`, `tests/test_mood_sector.py` and this section together.

---

## Part B: Current internals

Source files: [`mood/palettes.py`](../../mood/palettes.py) (curated data) ·
[`mood/engine.py`](../../mood/engine.py) (cosine crossfade) ·
[`mood/scene_policy.py`](../../mood/scene_policy.py) (scene rules + debounce) ·
[`mood/service.py`](../../mood/service.py) (front door) ·
[`core/Mode_master.py`](../../core/Mode_master.py), [`core/CommandRouter.py`](../../core/CommandRouter.py), [`core/TransitionBridge.py`](../../core/TransitionBridge.py), [`modes/Mode.py`](../../modes/Mode.py) (outside glue).

### Crossfade
`mood = from + (to - from) * w`, with `w = 0.5 * (1 - cos(pi * progress))`, default duration 2 s. A new request starts from the **currently blended** colours, so changing target mid-fade never jumps. Re-requesting the active target is a no-op (the timer is not reset).

### Scene-driven palettes (auto-mode)
Off by default (code default of `create_mood_service(auto_scene=False)`; no config key for now). When enabled, `update(dt, scene)` asks for the palette below after the scene has persisted for the dwell time.

| Scene | Palette | Dwell |
| :--- | :--- | :-: |
| `CHILL`, `DEEP_AMBIENT`, `FLOATING_PULSE` | Deep Ocean | 3 s |
| `GROOVE`, `THE_POCKET`, `CHAOTIC_FILL` | Cyberpunk | 3 s |
| `BUILDUP`, `PRE_DROP_BUILDUP` | Solar Ember | 3 s |
| `DROP_IMPACT` | Neon Acid | 0 s |

There is **no manual hold**: a manual `select_mood` always works at once, and the next scene change lets auto-mode take over again. Scenes with no entry (e.g. `STRUCTURAL_CHANGE`) change nothing.

### Guarantees
- AXIOM-01: `update` <= 0.01 ms. AXIOM-02: zero allocation in `update`. Both covered by `tests/test_mood_sector.py`.
- AXIOM-07: every file in `mood/` <= 500 lines.
