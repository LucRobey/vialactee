---
name: vialactee-mode-creator
description: Guidelines, vectorization rules, boilerplate templates, and settings schemas for authoring and modifying visual animation modes in the Vialactée chandelier project. Use when creating, modifying, or debugging modes in the modes/ directory.
---

# Vialactée Visual Mode Authoring Skill

Use this skill whenever you are writing, refactoring, or optimizing visual light animation modes inside the `modes/` directory.

## Core Principles & Rules

### 1. Class Inheritance & Execution Method
* Every mode **must** subclass `Mode` from `modes.Mode`.
* **Override `run(self)`**: Never override `update()`. The base class `update()` handles internal state management and performance timing.
* Keep `__init__` signature standard:
  ```python
  def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
      super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
  ```

### 2. Strict NumPy Vectorization (Zero Python Loops on LEDs)
To maintain 60 FPS across all 1,304 LEDs on the Raspberry Pi:
* **NEVER** write `for i in range(self.nb_of_leds)` or loop over indices.
* Precompute spatial arrays (e.g. `np.linspace(0.0, 1.0, self.nb_of_leds)`) in `__init__`.
* Compute arrays for Hue, Saturation, and Value shaped `(nb_of_leds,)`.
* Convert colors via `RGB_HSV.fromHSV_toRGB_vectorized(h, s, v)` which returns a 2D `(nb_of_leds, 3)` RGB array.
* Apply fades and blends using base class helper methods:
  - `self.smooth_vectorized(ratio, target_rgb_matrix)`: Blends current frame with target matrix.
  - `self.smooth_segment_vectorized(ratio, start, stop, target_color_or_array)`: Blends a range of LEDs.
  - `self.fade_to_black(ratio)` or `self.fade_to_black_segment_vectorized(ratio, start, stop)`.

### 3. Dynamic Settings & React Webapp Exposure
Avoid hardcoding magic constants in color math. Fetch default parameters from `self.infos.get("param_name", default_val)` and expose them via `get_settings_schema()`:
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

### 4. Audio & Rhythm Reactivity
* Access audio data via `self.listener`.
* Consult [listener_api.md](./references/listener_api.md) for full descriptions of `asserved_fft_band`, `beat_phase`, `is_real_beat`, `beat_tag`, and `chroma_values`.

### 5. Reference Implementation
* Inspect [boilerplate_mode.py](./examples/boilerplate_mode.py) for a complete, production-ready template.

### 6. Mode Registration
When adding a new mode:
1. Create the mode file in `modes/<ModeName>_mode.py`.
2. Register the mode in `modes/modes_description.md` with visual description, orientation, and parameter schema.
3. Register the mode entry in [`config/modes.json`](file:///c:/Users/Users/Desktop/vialact%C3%A9e/vialactee/config/modes.json):
   ```json
   {
     "name": "Display Name",
     "module": "<ModeName>_mode",
     "class": "<ModeName>_mode"
   }
   ```
   Each segment in `core/Segment.py` reads `modes.json` on boot and dynamically imports/instantiates the mode.
