# Mood Sector Contract (`mood_contract.md`)

Sibling of [`music_analyzer_contract.md`](music_analyzer_contract.md) and [`transition_contract.md`](transition_contract.md). The mood sector lives in [`mood/`](../../mood/) and is a **sealed room**: it talks to the rest of the project only through the doors below, defined in code in [`mood/api.py`](../../mood/api.py).

## Part A: The Doors & Trust Upgrade (authoritative)

**Wall rules** (enforced by [`tests/governance/test_mood_isolation.py`](../../tests/governance/test_mood_isolation.py))
1. Nothing in `mood/` imports project code (`core/`, `music/`, `modes/`, `connectors/`, `hardware/`, `transitions/`, ...). Only the standard library and `numpy`.
2. Nothing outside `mood/` imports from it except `mood.api`.
3. `api.py` uses only the standard library and `numpy`.
4. The front door is **synchronous**.
5. Sibling sectors never import each other: `core/` glue translates (for example `PaletteRequest` from `transitions.api` becomes `MoodService.request_palette`).

### Trust Transformation Across the Wall

`mood/` acts as a **temporal shock absorber** that upgrades an 🟠 **LOW-trust** heuristic (`scene`) into 🟢 **HIGH-trust** visual signals:
* **Input (`scene` — 🟠 LOW trust):** Macro scene classification (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) from `music/` can jitter or false-trigger on complex transients.
* **Outputs (`colors()` and `modifiers()` — 🟢 HIGH trust *as consumed*):** Because `mood/` applies a `0.30 s` debounce + `2.5 s` cosine crossfade to `modifiers()` and a `4.0 s` dwell + `3.0 s` cosine crossfade to `colors()`, modes can consume `self.mood_colors` (`self.palette_lut`, `self.highlight_color`) and `self.mood_modifiers` (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`) directly on every frame without any branching or secondary smoothing.

| # | Door | Dir | Trust | Shape (in `api.py`) | Notes |
| :-: | :--- | :-: | :-: | :--- | :--- |
| 1 | Clock + scene | in | 🟠 LOW (`scene`) | `update(dt, scene)` | Called every frame by `Mode_master`. `scene` is a plain string (e.g. `"BUILDUP"`), optional. |
| 2 | Requests | in | ⚙️ UI / Glue | `request_palette(name, duration)`, `next_palette()`, `set_auto_scene(enabled)` | UI selection (`select_mood`) and transition palette requests arrive here. Unknown names return `False`. |
| 3 | Colours | out | 🟢 HIGH *(as consumed)* | `colors()` | One **read-only** `(4, 3)` `int32` array `[primary, secondary, accent, background]`. Always the same object, updated in place: zero allocation. |
| 4 | Modifiers | out | 🟢 HIGH *(as consumed)* | `modifiers()` | One **read-only** `(4,)` `float32` array `[pace, sharpness, trail, accent_mix]`. Smoothly cosine-crossfaded over 2.5 s after a 0.30 s scene debounce (decoupled from `auto_scene`): zero allocation. |
| 5 | Status | out | 🟢 HIGH | `get_status()` -> `MoodStatus` | Palette, target, progress, transitioning, available palettes, auto-scene flag. Feeds `activeMood` / `availableMoods` in the UI snapshot. |

**Ownership.** The room owns: the curated palettes, the cosine crossfade, the scene-to-palette rules, and the bounded scene modifiers. The outside owns: when to call it, the UI, and what modes do with the colours and modifiers. Modes never import `mood`: `Mode_master` binds the live views once with `Mode.bind_mood_colors(mood.colors())` and `Mode.bind_mood_modifiers(mood.modifiers())`, and modes read `self.mood_colors` and `self.mood_modifiers` (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`). `Mode.reset_mood_colors()` / `Mode.reset_mood_modifiers()` restore static fallbacks for tests.

**Change policy.** Inside the room anything may change freely. Changing a door means editing `api.py`, `tests/test_mood_sector.py` and this section together.

---

## Part B: Current internals

Source files: [`mood/palettes.py`](../../mood/palettes.py) (curated data) ·
[`mood/engine.py`](../../mood/engine.py) (cosine crossfade for colours and modifiers) ·
[`mood/scene_policy.py`](../../mood/scene_policy.py) (scene rules + debounce governors) ·
[`mood/service.py`](../../mood/service.py) (front door) ·
[`core/Mode_master.py`](../../core/Mode_master.py), [`core/CommandRouter.py`](../../core/CommandRouter.py), [`core/TransitionBridge.py`](../../core/TransitionBridge.py), [`modes/Mode.py`](../../modes/Mode.py) (outside glue).

### Crossfade
`mood = from + (to - from) * w`, with `w = 0.5 * (1 - cos(pi * progress))`, default manual duration 2.0 s (auto-scene palette duration 3.0 s; modifier crossfade duration 2.5 s). A new request starts from the **currently blended** colours or modifiers, so changing target mid-fade never jumps. Re-requesting the active target is a no-op (the timer is not reset).

### Scene-driven palettes (auto-mode) & Always-on Scene Modifiers
Palette auto-mode is off by default in `mood.api` (enabled in `Mode_master` via `create_mood_service(auto_scene=True)`). When enabled, `update(dt, scene)` requests the palette below after the scene has persisted for the `4.0 s` dwell time (preventing short `1.5 s` drops from hijacking the palette).

Meanwhile, `modifiers()` is **always** updated whenever `scene` is passed to `update(dt, scene)` (even when `auto_scene=False`), using a `0.30 s` debounce (`ModifierGovernor`) followed by a `2.5 s` cosine crossfade:

| Scene | Palette (`auto_scene=True`) | Palette Dwell | `pace` | `sharpness` | `trail` | `accent_mix` |
| :--- | :--- | :-: | :-: | :-: | :-: | :-: |
| `CHILL` | Deep Ocean | 4.0 s | `0.82` | `0.78` | `1.18` | `0.00` |
| `GROOVE` | Cyberpunk | 4.0 s | `1.00` | `1.00` | `1.00` | `0.05` |
| `BUILDUP` | Solar Ember | 4.0 s | `1.12` | `1.12` | `0.92` | `0.15` |
| `DROP_IMPACT` | Neon Acid | 4.0 s | `1.22` | `1.22` | `0.88` | `0.28` |

There is **no manual hold**: a manual `select_mood` always works at once, and the next debounced scene change lets auto-mode take over again. Scenes with no entry (any name other than the 4 above) change nothing.

### Guarantees
- AXIOM-01: `update` <= 0.01 ms. AXIOM-02: zero allocation in `update`. Both covered by `tests/test_mood_sector.py`.
- AXIOM-07: every file in `mood/` <= 500 lines.
