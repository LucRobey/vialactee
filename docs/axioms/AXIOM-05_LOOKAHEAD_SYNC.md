# AXIOM-05: Predictive Lookahead & Speaker Back-Projection

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/test_audio_pipeline.py`, `core/Listener.py`, `core/MultiBandOnsetAudioAnalyzer.py`  

---

## 1. Specification

1. **Audio-Visual Latency Bound:**
   Perceptual audio-visual alignment tolerance between physical speaker sound wave emission and chandelier optical flash is strictly bounded:
   $$\Delta t_{\text{AV}} < \mathbf{50.0\text{ ms}}$$
2. **Predictive Lookahead Ring Buffer:**
   Audio ingestion maintains a 5.0-second non-causal circular lookahead buffer. Feature extraction, onset detection, and beat tracking execute ahead of time within this lookahead horizon.
3. **Speaker Time ($T_{\text{speaker}}$) Back-Projection Formula:**
   Visual animations must never align to the raw ingest timestamp $T_{\text{ingest}}$. Phase ($\theta$) and beat arrival timestamps must be mathematically back-projected to real-world speaker cone emission time:
   $$T_{\text{speaker}} = T_{\text{ingest}} - 5.0\text{ s} - \Delta t_{\text{dynamic\_latency}} - \Delta t_{\text{hardware\_latency}}$$
   where:
   - $5.0\text{ s}$: Fixed lookahead delay buffer.
   - $\Delta t_{\text{dynamic\_latency}}$: Measured dynamically via PortAudio `inputBufferAdcTime` timestamps.
   - $\Delta t_{\text{hardware\_latency}}$: Calibrated physical audio interface and DAC latency.
4. **Phase Continuity Invariant:**
   The continuous phase variable $\theta \in [0.0, 1.0)$ presented to modes via `listener.beat_phase` must continuously advance relative to $T_{\text{speaker}}$ without abrupt discontinuities.

---

## 2. Synchronization Pipeline

```
Raw Audio Ingestion (T_ingest)
        │
        ▼
5.0s Lookahead Ring Buffer (DSP & MIR Beat Tracking Ahead of Time)
        │
        ▼
Back-Projection Equation: T_speaker = T_ingest - 5.0s - Δt_dyn - Δt_hw
        │
        ▼
Physical LED Flash ◄── <50ms AV Sync ──► Speaker Acoustic Waveform
```

---

## 3. Violation Conditions

- Visual modes rendering beats timed to $T_{\text{ingest}}$ rather than $T_{\text{speaker}}$.
- Audio-visual skew exceeding 50.0 ms.
- Hard phase snapping causing visible visual stutter when adjusting beat estimates.
