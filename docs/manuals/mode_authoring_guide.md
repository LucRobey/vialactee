# Mode Authoring Guide

> **Location:** `docs/manuals/mode_authoring_guide.md` (Tier 2 Operational Manual)  
> **Sector Contract:** [`docs/contracts/mode_contract.md`](../contracts/mode_contract.md)  
> **Reference Catalog:** [`docs/reference/modes_catalog.md`](../reference/modes_catalog.md)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)

This guide walks you through authoring high-performance, audio-reactive visual animation modes for the Vialactée chandelier. For the formal sector boundary contract, input/output doors, and signal trust rules, see [`docs/contracts/mode_contract.md`](../contracts/mode_contract.md).

---

## 0. Before You Write Code: The Four-Question Worksheet

Before writing or refactoring a mode, answer these four questions explicitly (see **Law 7: One Lead Timescale** in [`docs/contracts/mode_contract.md`](../contracts/mode_contract.md)):

1. **What does this mode *show*?** (loudness, beat, balance, timbre, history, event). Pick **one** answer.
2. **What is its lead driver?** Which single signal (`beat`, `level`, `spectrum`, or `transient`) moves the main shape (size, position, or primary brightness)? What optional secondary driver (`SECONDARY`) adds detail (~20% of motion)?
3. **What does it do at `rhythm_lock == 0`?** (Law 1: when the beat flywheel unlocks, the mode must stay alive via continuous acoustic energy, spectrum, or free phase.)
4. **Which dimensions does the mood control?** (color palette, trail length via `mood_trail`, global speed via `mood_pace`, and how `ctx.tension` bends the lead by at most ±30%.)

Every mode records its answer on the class (`LEAD`, `SECONDARY`) and in a `Lead:` line inside its class docstring.

---

## 1. The `Mode` Base Class Lifecycle

Every visual animation subclasses `modes.Mode.Mode` ([`modes/Mode.py`](../../modes/Mode.py)).

- **Target Buffer:** Modes render directly into `self.rgb_list`, a pre-allocated 2D NumPy array of shape `(nb_of_leds, 3)` (`dtype=np.int32`, RGB values in `0..255`).
- **`render()` vs `run()`:**
  - Modern modes override:
    ```python
    def render(self, buffer=None, audio_ctx=None, frame_info=None):
    ```
  - Legacy `run(self)` remains 100% supported: `Mode.render()` redirects `self.rgb_list` to the target buffer (either the active buffer or `Segment.dual_rgb_list` during a dual-mode transition), invokes `self.run()`, and restores `self.rgb_list` in a `finally:` block.
  - **Never override `update()`** — `Mode.update()` delegates to `self.render()`.
- **Base Vectorized Utilities:**
  - `self.smooth_vectorized(ratio, target_rgb_matrix)` / `self.smooth_segment_vectorized(ratio, start, stop, target_color)`
  - `self.fade_to_black(ratio)` / `self.fade_to_black_segment_vectorized(ratio, start, stop)`
  - `self.palette_lut` (`(256, 3)` gradient) and `self.palette_sample(t, out)`
  - `self.highlight_color` (luminance-safe flash color)
  - Timing helpers: `self.dt`, `self.fps_ratio` (`self.dt * 60.0`), and `self.alpha(rate_hz)` ($1 - e^{-\text{dt} \cdot \text{rate\_hz}}$)
  - Audio/rhythm helpers: `self.rhythm_lock`, `self.beat_pulse(sharpness=2.2)`, `self.drop_hit`, `self.drop_decay`
  - Mood modifiers: `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`

---

## 2. Dynamic Settings Schema (`get_settings_schema`)

Every mode can expose live-tunable parameters to the Web UI (`ModeSettings.tsx`) and `tools/mode_studio.py` by overriding `get_settings_schema(self)`:

```python
def get_settings_schema(self) -> List[Dict[str, Any]]:
    return [
        {
            "key": "pulse_decay",
            "label": "Pulse Decay",
            "control": "slider",          # "slider" | "toggle" | "list"
            "valueType": "number",        # "number" | "integer" | "boolean" | "string"
            "min": 0.50,
            "max": 0.99,
            "step": 0.01,
            "default": 0.90,
            "unit": "",
            "attr": "pulse_decay"         # Automatically bound to self.pulse_decay
        }
    ]
```

- When an operator adjusts a parameter in the Web UI (`set_mode_setting`), `Mode.apply_settings()` validates, clamps, and sets `getattr(self, attr)` on all active segment instances and invokes `self.on_settings_applied(applied)`.
- `Mode_master` persists overrides under `mode_settings` in `config/app_config.json`.
- **Rule:** Every setting declared in `get_settings_schema()` must be read in `run()` / `render()`.

---

## 3. Boilerplate Template

```python
from typing import Dict, Any, List
import numpy as np
from modes.Mode import Mode

class Custom_pulse_mode(Mode):
    """A template audio-reactive pulse mode (30 FPS, zero runtime heap allocations)."""

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.pulse_decay = float(infos.get("custom_pulse_decay", 0.90))
        self._intensity = 0.0
        self._color_buf = np.zeros(3, dtype=np.float64)

    def get_settings_schema(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "custom_pulse_decay",
                "label": "Pulse Decay",
                "valueType": "number",
                "min": 0.5,
                "max": 0.99,
                "step": 0.01,
                "default": 0.90,
                "attr": "pulse_decay"
            }
        ]

    def run(self) -> None:
        if self.nb_of_leds <= 0:
            return
        ctx = getattr(self.listener, "context", None)
        if ctx is not None and ctx.is_silent:
            self.fade_to_black_segment_vectorized(0.25, 0, self.nb_of_leds - 1)
            return

        # 1. Verified transient kick or 1-frame drop_hit (see docs/contracts/mode_contract.md)
        is_real = bool(ctx.is_real_beat) if ctx is not None else bool(getattr(self.listener, "is_real_beat", False))
        if (getattr(self.listener, "is_beat", False) and is_real and self.rhythm_lock > 0.35) or self.drop_hit:
            self._intensity = 1.0
        else:
            self._intensity *= self.pulse_decay ** self.fps_ratio

        # 2. Confidence-blended envelope fallback
        drive = max(self._intensity, self.beat_pulse(2.2)) * self.transition_scale
        np.multiply(self.mood_colors[0], drive, out=self._color_buf)
        self.smooth_segment_vectorized(self.alpha(12.0), 0, self.nb_of_leds - 1, self._color_buf)
```

---

## 4. Registration & Testing Workflow

1. Place your mode in `modes/Your_new_mode.py`.
2. Register in [`config/modes.json`](../../config/modes.json) with its 4-float `dna` vector and controlled vocabulary `tags` (`lead:<LEAD>` must match the class `LEAD` attribute):
   ```json
   {
     "name": "Your New Mode",
     "module": "Your_new_mode",
     "class": "Your_new_mode",
     "dna": { "energy": 0.60, "punch": 0.70, "rhythm": 0.80, "complexity": 0.40 },
     "tags": ["lead:beat", "form:bar", "origin:center", "color:palette", "layer:pulse"]
   }
   ```
3. Document the mode in [`docs/reference/modes_catalog.md`](../reference/modes_catalog.md) and update the mode count in [`docs/README.md`](../README.md) and [`docs/architecture/system_overview.md`](../architecture/system_overview.md).
4. Profile and tune interactively in Mode Studio:
   ```bash
   python tools/mode_studio.py --mode "Your New Mode"
   ```
5. Verify contract compliance and zero-allocation invariants:
   ```bash
   python -m pytest tests/test_all_modes_musical_context.py tests/test_mode_helpers.py tests/governance/
   ```
