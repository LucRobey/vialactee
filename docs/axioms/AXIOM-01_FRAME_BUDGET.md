# AXIOM-01: Real-Time Frame Budget & Execution Pacing

**Tier:** Tier 0 (Untouchable Golden Axiom)  
**Status:** Inviolable Law  
**Enforcement:** `tests/governance/test_axiom_01_frame_budget.py`, `config/app_config.json`  

---

## 1. Specification

1. **Physical Visual Framerate Target:**
   The physical LED rendering pipeline targets **30.0 FPS** (33.33 ms total frame budget).
2. **Execution Bound on Target Hardware:**
   Total per-frame compute across the pipeline (Audio DSP feature ingestion + active mode rendering across all segments + spatial blending/transitions + UDP network packetization) must complete in $\le \mathbf{20.0}\text{ ms}$ on ARM Cortex-A72 (Raspberry Pi 4B).
3. **Headroom Reserve:**
   A minimum timing margin of **13.33 ms (40%)** is permanently reserved for Linux kernel scheduling, ALSA audio buffer reads, thread context switches, and network I/O.
4. **ODF Sampling Decoupling:**
   The internal audio onset feature extractor in `core/MultiBandOnsetAudioAnalyzer.py` samples at **60.0 Hz** to preserve sub-millisecond temporal resolution for onset detection, while visual rendering paces at **30.0 FPS**.
5. **Configuration Alignment:**
   `config/app_config.json` must declare `"target_fps": 30` and `"alert_threshold_ms": 20.0`. Contradictory settings (e.g. 60 FPS visual targets) violate this axiom.

---

## 2. Mathematical Budget Breakdown

$$\begin{aligned}
T_{\text{frame}} &= 33.33\text{ ms} \quad (30\text{ FPS}) \\
T_{\text{compute\_budget}} &\le 20.00\text{ ms} \\
T_{\text{margin}} &\ge 13.33\text{ ms} \quad (40\%)
\end{aligned}$$

Expected component allotments on ARM Cortex-A72:
- **Audio DSP & Feature Extraction:** $\le 3.5\text{ ms}$
- **Segment Modes Rendering (up to 11 segments):** $\le 10.0\text{ ms}$
- **Spatial Transitions & Blending:** $\le 3.5\text{ ms}$
- **Hardware Packaging & Network Push:** $\le 3.0\text{ ms}$
- **Total Compute:** $\le 20.0\text{ ms}$

---

## 3. Violation Conditions

- Any single frame compute exceeding 20.0 ms during steady-state rendering.
- `app_config.json` declaring `target_fps` other than 30 or `alert_threshold_ms` other than 20.0.
- Synchronous blocking calls (such as `time.sleep()`, file read/write, synchronous HTTP) occurring inside the visual rendering loop.
