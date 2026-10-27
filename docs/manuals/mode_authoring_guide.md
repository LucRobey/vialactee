# Mode Authoring Guide

> **Location:** `docs/manuals/mode_authoring_guide.md` (Tier 2 Operational Manual)  
> **Reference Catalog:** [`docs/reference/modes_catalog.md`](../reference/modes_catalog.md)  
> **Enforcing Axioms:** [AXIOM-01](../axioms/AXIOM-01_FRAME_BUDGET.md), [AXIOM-02](../axioms/AXIOM-02_ZERO_ALLOCATION.md), [AXIOM-06](../axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)

This guide walks you through authoring high-performance, audio-reactive visual animation modes for the Vialactée chandelier.

---

## 1. The Mode Base Class Contract

Every visual animation subclasses `modes.Mode.Mode`.
- **Target Buffer:** Modes render directly into `self.rgb_list` (a NumPy 2D array of shape `(nb_leds, 3)`, `dtype=np.int32`).
- **Signature:** Modern modes override:
  ```python
  def render(self, buffer=None, audio_ctx=None, frame_info=None):
  ```
  or the legacy `run(self):` method.

---

## 2. Invariant Rules for Mode Authors

### Rule 1: Zero Dynamic Allocations in Hot Path (AXIOM-02)
- Never create NumPy arrays inside `run()` or `render()`.
- Pre-allocate all scratch buffers in `__init__()`.
- Use in-place mutations: `self.rgb_list.fill(0)`, `self.rgb_list[:] = self.color`, or `np.copyto()`.

### Rule 2: Perceptual Invariance & Real-Beat Gating (AXIOM-06)
- High-energy strobes and boundary impacts must check `self.listener.is_real_beat`.
- When beat trust drops, decay smoothly to acoustic power breathing (`self.listener.asserved_total_power`). Never cut abruptly to black.

### Rule 3: Frame-Rate Independence (`self.dt`, `self.fps_ratio`, `self.alpha()`)
- Always scale kinematics with the base-class timing helpers on `Mode`:
  - `self.dt`: elapsed seconds since the previous frame (falls back to `1/60` when unavailable).
  - `self.fps_ratio`: frame duration relative to 60 Hz (`self.dt * 60.0`; `1.0` at 60 Hz, `2.0` at 30 FPS).
  - `self.alpha(rate_hz)`: frame-rate independent smoothing factor $1 - e^{-\text{dt} \cdot \text{rate\_hz}}$.

### Rule 4: Handling Signals by Trust & Subtle Mood Governance (`modes/MODE_RULES.md`)
- Follow the Mode Sector Contract in [`modes/MODE_RULES.md`](../../modes/MODE_RULES.md). Per-signal trust is stated only in [`music_analyzer_contract.md`](../contracts/music_analyzer_contract.md); trust is guidance, not a test-enforced rule:
  - **🟢 HIGH trust:** safe to drive visuals directly every frame (physical spectral/power signals and the cosine-smoothed mood modifiers `self.mood_pace`, `self.mood_sharpness`, `self.mood_trail`, `self.mood_accent`).
  - **🟡 MEDIUM trust:** when reading tempo/phase signals (`beat_phase`, `is_beat`, `bpm`, `is_real_beat`, `beat_count`), blend or gate with `self.rhythm_lock` or `self.beat_pulse(sharpness)` so visuals stay alive when `beat_trust == 0.0`.
  - **🟠 LOW trust:** avoid reading or branching on heuristic scene/drop/boundary signals (for example `context.scene`, `is_drop_impact`, `is_song_change`) in concrete modes; use `self.mood_*` modifiers and the sanctioned `self.drop_hit` (1-frame trigger) and `self.drop_decay` ($1 \to 0$ envelope) helpers on `Mode`.

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

        # 1. Verified transient kick or 1-frame drop_hit
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

## 4. Registration Workflow

1. Place your mode in `modes/Your_new_mode.py`.
2. Register in `config/modes.json`:
   ```json
   {
     "name": "Your New Mode",
     "module": "Your_new_mode",
     "class": "Your_new_mode"
   }
   ```
3. Restart `Main.py`. The mode is immediately mounted and selectable via the Web App!
