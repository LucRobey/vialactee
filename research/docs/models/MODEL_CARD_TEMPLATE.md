# Model Card / Specification Template: `<ModelName>`

> **Model Identifier:** `<ModelName>`  
> **Author:** `<AuthorName or Agent ID>`  
> **Date:** `<YYYY-MM-DD>`  
> **Version:** `1.0.0`  
> **Base Class:** [`core.BaseAudioAnalyzer.BaseAudioAnalyzer`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/BaseAudioAnalyzer.py)  
> **Implementation File:** [`research/experiments/models/<ModelName>.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/research/experiments/models/)

---

## 1. Executive Summary & Problem Statement

### 1.1 Targeted Failure Phenomena
Describe the precise musical, perceptual, or DSP failure modes this architecture is engineered to resolve:
- `PHASE_INVERSION_UPBEAT`: 180° anti-phase lock caused by syncopated off-beat high-frequency transients (e.g. funk/disco hi-hats).
- `GHOST_BEAT_BURST`: Spurious beat triggers during quiet breakdowns, vocal cadenzas, or sparse passages.
- `HIGH_PHASE_JITTER`: Microtiming wobble exceeding the human visual threshold ($\ge 25\text{ms}$).
- `TRIPLE_METER_DRIFT`: Polyrhythmic confusion on 3/4 or 6/8 meters (e.g. waltzes).
- `LIVE_TEMPO_INERTIA`: Excessive flywheel lag or overshoot during expressive human tempo acceleration/deceleration.

### 1.2 Core Hypothesis
State the scientific hypothesis under test:
> *Example: By attenuating spectral flux above 3 kHz during the coarse tempo-class sweep, the periodic estimator will favor low-frequency kick fundamentals over syncopated hi-hats, eliminating upbeat phase traps without increasing phase jitter.*

---

## 2. Mathematical Formulations

### 2.1 Onset Detection Function ($ODF(t)$)
Define how raw multi-band FFT audio is transformed into the 1D novelty signal:
$$ODF(t) = \sum_{b=0}^{B-1} w_b \cdot \max\left(0, E_b(t) - E_b(t - \Delta t)\right)$$
Where $w_b$ are band weightings, and $E_b(t)$ is the smoothed logarithmic energy in frequency band $b$.

### 2.2 Periodic & Tempo Metric
Specify the tempo estimation equations:
- **Harmonic Logarithmic Tempo-Class:**
  $$c = \log_2\left(\frac{\text{BPM}}{60}\right) \pmod 1$$
- **Correlation Metric:** (e.g. Pearson correlation, Fast Fourier Comb, or Comb Filter Autocorrelation):
  $$r(\text{BPM}, \phi) = \frac{\mathbf{t}_{\text{BPM}, \phi} \cdot (\mathbf{x} - \bar{x})}{\|\mathbf{x} - \bar{x}\|_2}$$

### 2.3 Continuous Phase Flywheel & Synchronization Dynamics
Specify the phase accumulator and soft-snapping behavior:
- **Free Evolution:**
  $$\phi(t) = \phi(t - \Delta t) + \frac{\text{BPM}(t)}{60} \Delta t \pmod 1$$
- **Phase Correction / Soft-Snapping:**
  $$\Delta \phi = \text{clamp}\left(\phi_{\text{target}} - \phi, -\Delta\phi_{\max}, +\Delta\phi_{\max}\right)$$
- **Boundary Clamps & Refractory Lockout:**
  - **Backward Wrap Clamp:** Prevent phase from wrapping backwards across $0.0$ when $\phi < 0.25$.
  - **Physical Refractory Period:**
    $$T_{\min} = \max\left(T_{\text{abs\_floor}}, k_{\text{refractory}} \times \frac{60}{\text{BPM}}\right)$$

### 2.4 Beat Validation Gates
Conditions under which a predicted beat event is confirmed (`is_real_beat = True` vs `is_dropped_beat = True`):
- Absolute transient floor: $E_{\text{transient}} \ge E_{\text{floor}}$
- Baseline ratio: $E_{\text{transient}} \ge k_{\text{ratio}} \cdot \bar{E}_{\text{rolling}}$

---

## 3. Subclass Constructor & API Contract

Every candidate model must adhere strictly to the `BaseAudioAnalyzer` lifecycle contract:

```python
from typing import Dict, Any, Optional
import numpy as np
from core.BaseAudioAnalyzer import BaseAudioAnalyzer
from core.RhythmConfig import RhythmConfig

class CandidateModel(BaseAudioAnalyzer):
    def __init__(
        self,
        ingestion: Any = None,
        infos: Optional[Dict[str, Any]] = None,
        config: Optional[RhythmConfig] = None
    ) -> None:
        super().__init__(ingestion=ingestion, infos=infos, config=config)
        self.config = config or RhythmConfig()
        # Initialize custom buffers here

    def reset(self) -> None:
        """Reset internal phase accumulators and history buffers."""
        super().reset()
        ...

    def update(self, current_time: float, dt: float, fps_ratio: float) -> None:
        """Execute per-frame 60 FPS analysis."""
        ...

    def capture_frame_telemetry(self) -> Dict[str, Any]:
        """Capture time-series tensors for AI failure analysis."""
        return {
            "bpm": float(self.bpm),
            "beat_phase": float(self.speaker_phase),
            "confidence": float(self.confidence_score),
            "custom_flux": float(getattr(self, "current_flux", 0.0)),
        }
```

---

## 4. Hyperparameter Catalog

| Parameter | Type | Default | Valid Range | Physical Units | Musical / Algorithmic Meaning |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `high_snap_ratio` | `float` | `0.50` | `[0.0, 1.0]` | Normalized | Phase correction gain during high-confidence detection |
| `real_beat_energy_floor` | `float` | `5.0` | `[0.5, 50.0]` | Energy units | Minimum onset flux required to trigger visual flash |
| `sweep_interval` | `float` | `0.20` | `[0.05, 1.0]` | Seconds | Interval between full Pearson template correlation sweeps |

---

## 5. Complexity & Real-Time Performance Budget

- **Computational Complexity:** $\mathcal{O}(\dots)$ per frame.
- **Memory Footprint:** Dynamic heap allocations per frame must be strictly **zero** (pre-allocated NumPy buffers).
- **Target CPU Budget:** $\le 3.0\text{ms}$ per 60 FPS frame on Raspberry Pi 4 / 5.
- **Empirical Execution Time (Simulation Benchmark):** `X.XX ms` per frame.

---

## 6. Empirical Benchmark Results

### 6.1 Scorecard Summary

| Suite | Model | F1@50ms | CMLt | AMLt | Upbeat Gap | Phase Jitter | CPU/frame |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Synthetic** | Candidate | 00.0% | 00.0% | 00.0% | 0.00 | 0.0ms | 0.00ms |
| **Neural Core** | Candidate | 00.0% | 00.0% | 00.0% | 0.00 | 0.0ms | 0.00ms |

### 6.2 Genre & Style Performance Breakdown

| Musical Genre | Tracks ($n$) | F1@50ms (Candidate) | F1@50ms (Baseline) | $\Delta$ F1 | Primary Failure Mode |
| :--- | :---: | :---: | :---: | :---: | :--- |
| Electronic / Synthwave | - | -% | -% | -% | - |
| Disco / Funk | - | -% | -% | -% | - |
| Classic / Hard Rock | - | -% | -% | -% | - |
| Pop / Pop-Rock | - | -% | -% | -% | - |
| Chanson / Acoustic | - | -% | -% | -% | - |
| Latin / World | - | -% | -% | -% | - |

---

## 7. Status & Promotion Recommendation

- **Current Status:** `DRAFT` / `BENCHMARKED` / `PROMOTED TO PRODUCTION` / `ABANDONED`
- **Zero-Regression Gate:** Must show $\Delta \text{F1} \ge 0.0\%$ on the synthetic clean-room suite.
- **Decision Rationale:** Summary of findings and recommendations.
