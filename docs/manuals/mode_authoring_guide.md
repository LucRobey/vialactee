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

### Rule 3: Frame-Rate Independence
- Always scale kinematics with `self.infos.get("fps_ratio", 1.0)` or `delta_time`.

### Rule 4: Musical Context & Regimes Integration
- Prefer declarative state branching via `self.listener.context.current_regime` (`THE_POCKET`, `FLOATING_PULSE`, `DEEP_AMBIENT`, `CHAOTIC_FILL`, `PRE_DROP_BUILDUP`, `STRUCTURAL_CHANGE`).
- Interpolate parameter shifts using `self.listener.context.regime_blend` $\in [0.0, 1.0]$.

---

## 3. Boilerplate Template

```python
from typing import Dict, Any, List
import numpy as np
from modes.Mode import Mode
from utils.colors import white, blue, black

class Custom_pulse_mode(Mode):
    """A template audio-reactive pulse mode."""

    def __init__(self, name: str, segment_name: str, listener: Any, leds: Any, indexes: List[int], rgb_list: np.ndarray, infos: Dict[str, Any]):
        super().__init__(name, segment_name, listener, leds, indexes, rgb_list, infos)
        self.pulse_decay = float(infos.get("custom_pulse_decay", 0.90))
        self._intensity = 0.0

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

    def render(self, buffer=None, audio_ctx=None, frame_info=None):
        out_buf = self.rgb_list if buffer is None else buffer

        # Check beat gating
        if getattr(self.listener, "is_beat", False) and getattr(self.listener, "is_real_beat", False):
            self._intensity = 1.0
        else:
            self._intensity *= self.pulse_decay

        # Fallback to acoustic power on low confidence
        conf = getattr(self.listener, "beat_confidence", 1.0)
        if conf < 0.4:
            power = getattr(self.listener, "instant_power", 0.0)
            self._intensity = max(self._intensity, float(np.clip(power / 100.0, 0.0, 1.0)))

        # In-place buffer color write
        color = (0, int(150 * self._intensity), int(255 * self._intensity))
        out_buf[:] = color
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
