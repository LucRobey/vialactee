---
name: vialactee-mode-creator
description: "Vectorized NumPy light rendering, 30 FPS frame budget (AXIOM-01), Mode class inheritance, dynamic settings schemas, and audio-reactive kinetics/scene hooks in modes/. Use when creating, modifying, optimizing, or debugging visual lighting modes and choreographies."
---

# Vialactée Visual Mode Authoring Skill

Use this skill whenever you are writing, refactoring, or optimizing visual light animation modes inside the `modes/` directory.

## Core Principles & Rules

### 1. Class Inheritance & Execution Method
* Every mode **must** subclass `Mode` from `modes.Mode`.
* **Override `render(self, buffer=None, audio_ctx=None, frame_info=None)` or `run(self)`**:
  - `render(buffer=...)` is the preferred modern signature. If `buffer` is provided, the mode renders directly into it.
  - Legacy `run(self)` remains 100% backward compatible: `Mode.render()` automatically redirects `self.rgb_list` to the target buffer, executes `run()`, and safely restores `self.rgb_list`.
  - Never override `update()`. The base class `update()` handles internal state management and performance timing.
* Keep `__init__` signature standard:
  ```python
  def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
      super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
  ```

### 2. Strict NumPy Vectorization & Immutable Colors (Zero Memory Churn)
To maintain 30 FPS (AXIOM-01) across all 1,304 LEDs on the Raspberry Pi:
* **NEVER** write `for i in range(self.nb_of_leds)` or loop over indices.
* Precompute spatial arrays (e.g. `np.linspace(0.0, 1.0, self.nb_of_leds)`) in `__init__`.
* Compute arrays for Hue, Saturation, and Value shaped `(nb_of_leds,)`.
* Convert colors via `RGB_HSV.fromHSV_toRGB_vectorized(h, s, v, out=self._target_rgb)` into a pre-allocated `(nb_of_leds, 3)` RGB array, or sample `self.palette_lut` / `self.palette_sample(t, out)`.
* **Immutable Color Constants**: Color constants from `utils.colors` (`red`, `green`, `blue`, `white`, etc.) and `self.white` on `Mode` are defined as immutable tuples `(R, G, B)`. They can be assigned directly to NumPy arrays (`self.rgb_list[:] = self.white`) without risk of shared mutable state corruption across segments.
* Apply fades and blends using base class helper methods:
  - `self.smooth_vectorized(ratio, target_rgb_matrix)`: Blends current frame with target matrix.
  - `self.smooth_segment_vectorized(ratio, start, stop, target_color_or_array)`: Blends a range of LEDs.
  - `self.fade_to_black(ratio)` or `self.fade_to_black_segment_vectorized(ratio, start, stop)`.

### 3. Dynamic Settings & React Webapp Exposure
Avoid hardcoding magic constants in color math. Fetch default parameters from `self.infos.get("param_name", default_val)` and expose them via `get_settings_schema()`, ensuring every declared setting is read inside `run()`/`render()`:
```python
def get_settings_schema(self) -> List[Dict[str, Any]]:
    return [
        {
            "key": "speed",
            "label": "Animation Speed",
            "valueType": "number",
            "min": 0.1,
            "max": 5.0,
            "default": 1.0,
            "step": 0.1,
            "attr": "speed"  # Auto-binds to self.speed on live update
        }
    ]
```

### 4. Audio, Rhythm & Subtle Mood Reactivity
* Access audio data via `self.listener` and base `Mode` helpers (`self.rhythm_lock`, `self.beat_pulse(sharpness)`, `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`, `self.palette_lut`, `self.highlight_color`, `self.drop_hit`).
* Consult [`docs/contracts/music_analyzer_contract.md`](../../../docs/contracts/music_analyzer_contract.md) for full descriptions of `asserved_fft_band`, `beat_phase`, `is_real_beat`, `beat_tag`, and `chroma_values`.
* **Architectural Laws ([`docs/contracts/mode_contract.md`](../../../docs/contracts/mode_contract.md))**:
  - **Always Alive Without the Flywheel (`self.rhythm_lock == 0.0`):** Every mode must produce a smooth, musical animation driven by continuous audio energy, `nb_of_fft_band` spectrum (`asserved_fft_band`), or pitch even when `beat_trust == 0.0`. When mapping `num_bands` frequency bands to mood colors, sample across `self.palette_lut[int(b * 255 / max(1, num_bands - 1))]`.
  - **Rhythm-Locked When Confident (`self.rhythm_lock -> 1.0`):** Smoothly blend the same visual algorithm with `beat_phase`, `bpm`, and `self.beat_pulse(sharpness)` as `self.rhythm_lock` rises.
  - **No `if ctx.scene == ...` Branching in Modes:** Never write hard `if scene == ...` branches in modes. The sealed `mood/` sector absorbs scene changes (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`) with a `0.30s` debounce and `2.5s` cosine crossfade, exposing bounded modifiers (`self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`) on `Mode`.
  - **Gate Hard Flashes:** Use **Tier 3 Micro Badges** (`context.is_locked`, `context.is_real_beat`, `context.is_syncopated`) and sanctioned `Mode` helpers (`self.drop_hit`, `self.drop_decay`) to gate 1-frame transient impacts and strobes. Avoid reading heuristic flags (`scene`, `is_drop_impact`, `is_drop_imminent`, `is_song_change`, `is_verse_chorus_change`, `is_structural_cut`; trust per `music_analyzer_contract.md`) directly in concrete modes, and never flash blindly on ghost beats or lock into 1.5s full-strip whiteouts.
  - **Law 7 — One Lead Timescale ([`docs/contracts/mode_contract.md`](../../../docs/contracts/mode_contract.md#7-one-lead-timescale-the-choreography-doctrine)):**
    - **Three timescales:** **Macro** (seconds: `mood_pace`, `mood_sharpness`, `mood_trail`, `mood_accent`, palette, plus bounded `ctx.tension` / `drop_decay` modulators), **Meso** (beat to 1 s: `beat_pulse()`, `beat_phase`, `ctx.energy`), and **Micro** (frame to 100 ms: `asserved_fft_band`, `band_proportion`, `band_flux`, `spectral_tilt`, `vertical_center`).
    - **Four audio drivers + `macro` mute channel:** Every concrete mode class must declare `LEAD: str` and `SECONDARY: tuple[str, ...]` (0 or 1 entry, `!= LEAD`) from `DRIVERS = ("beat", "level", "spectrum", "transient")` in [`utils/choreography.py`](../../../utils/choreography.py), plus a `Lead: ...` line in the class docstring. (`macro` is a 5th mute channel used by tests and `tools/mode_studio.py` `[Ctrl+B/L/S/T/M]` / `[Ctrl+0]`, not a driver.)
    - **One visual dimension, one timescale:** The main shape (size, position, primary brightness) is driven by `LEAD` (~70% of visible motion); fine detail (edge shimmer, spark size, cap brightness) by at most one `SECONDARY` (~20%); color, trail, and global speed by **Macro** (~10%). Never sum three timescales onto the same visual variable.

### 5. Reference Implementation
* Inspect [boilerplate_mode.py](./examples/boilerplate_mode.py) for a complete, production-ready template.

### 6. Mode Registration
When adding a new mode:
1. Answer the Four-Question Worksheet in [`docs/manuals/mode_authoring_guide.md`](../../../docs/manuals/mode_authoring_guide.md) and create `modes/<ModeName>_mode.py` with `LEAD`, `SECONDARY`, and a `Lead:` class docstring line.
2. Register the mode in [`docs/reference/modes_catalog.md`](../../../docs/reference/modes_catalog.md) with `Lead`, `Secondary`, visual description, orientation, and parameter schema.
3. Register the mode entry in [`config/modes.json`](../../../config/modes.json) with its 4-float `dna` vector and controlled vocabulary `tags` (`lead:<LEAD>` must match the class `LEAD` attribute):
   ```json
   {
     "name": "Display Name",
     "module": "<ModeName>_mode",
     "class": "<ModeName>_mode",
     "dna": { "energy": 0.60, "punch": 0.70, "rhythm": 0.80, "complexity": 0.40 },
     "tags": ["lead:beat", "form:bar", "origin:center", "color:palette", "layer:pulse"]
   }
   ```
   Each segment in `core/Segment.py` reads `modes.json` on boot and dynamically imports/instantiates the mode, while `TransitionBridge.build_mode_profiles()` forwards `dna` and `tags` to the `transitions/` coherence engine.
