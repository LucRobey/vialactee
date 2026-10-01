# 🌌 Vialactée

**Vialactée** is an asynchronous, real-time Python orchestration server and audio-visual DSP engine designed to run on a Raspberry Pi 4B (and desktop simulation environments) to drive an interactive, mathematically mapped LED chandelier (1,304 WS2812B LEDs across 11 spatial segments).

It listens to acoustic room audio in real time, extracts dual-resolution Mel spectral features and onset derivatives, tracks musical rhythm and tempo with an Anticipation Flywheel ("Oracle"), and animates physical LED strips with zero-allocation NumPy vectorization and smooth spatial transitions.

---

## ⚡ Quick Start

### 1. Requirements & Setup
- Python 3.10+
- Recommended: create a virtual environment (`python -m venv venv && source venv/bin/activate` or `.\venv\Scripts\activate`)
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Run Desktop Simulation (Pygame GUI)
To launch the chandelier simulator on PC with a microphone or Spotify loopback:
```bash
python Main.py
```
This spawns:
- The async audio ingestion and beat tracking engine.
- The 22 active visual mode animations across all segments.
- The Pygame visualizer (`hardware/Fake_leds.py`) reconstructing chandelier geometry from `config/segments_small.json` or `config/segments_full.json`.
- The Web App API server on `http://localhost:8080` (if `startServer: true` in `config/app_config.json`).

### 3. Run Fast CI & Governance Verification
```bash
python -m pytest tests/test_code_governance.py
```

---

## 🏛️ Architecture & Governance Core

Vialactée is strictly governed by **The 9 Untouchable Golden Axioms (Tier 0)**:
1. **[AXIOM-01: Real-Time Frame Budget](./docs/axioms/AXIOM-01_FRAME_BUDGET.md)**: 30.0 FPS target, $\le 20.0\text{ ms}$ total compute budget on Pi 4B, 60 Hz audio ODF sampling.
2. **[AXIOM-02: Zero Dynamic Heap Allocations](./docs/axioms/AXIOM-02_ZERO_ALLOCATION.md)**: 0 heap allocations inside the render hot loop; decoupled WebSocket telemetry.
3. **[AXIOM-03: Physical Chandelier Geometry](./docs/axioms/AXIOM-03_HARDWARE_GEOMETRY.md)**: Unified JSON single truth; vertical strips physically wired bottom-up (`step.y = -1`).
4. **[AXIOM-04: Network Transport Protocols](./docs/axioms/AXIOM-04_NETWORK_PROTOCOLS.md)**: UDP datagrams $\le 1,202\text{ B}$ (safe from MTU fragmentation); $\le 10\text{ Hz}$ telemetry.
5. **[AXIOM-05: Predictive Lookahead Sync](./docs/axioms/AXIOM-05_LOOKAHEAD_SYNC.md)**: Speaker cone back-projection ($T_{\text{speaker}}$) with $< 50\text{ ms}$ perceptual sync.
6. **[AXIOM-06: Perceptual Invariance & Real-Beat Gating](./docs/axioms/AXIOM-06_PERCEPTUAL_RHYTHM.md)**: Graceful volume decay on low confidence; strobes gated by `is_real_beat`.
7. **[AXIOM-07: Code Governance & 500-Line Ratchet](./docs/axioms/AXIOM-07_CODE_GOVERNANCE.md)**: 500-line cap on production files; grandfathered files only shrink.
8. **[AXIOM-08: Clean-Room Zero-Regression Gate](./docs/axioms/AXIOM-08_RESEARCH_REGRESSION.md)**: Immutable benchmark ground truth; zero regression gate on beat models.
9. **[AXIOM-09: Scoped DSP Math Invariance](./docs/axioms/AXIOM-09_PLATFORM_AGNOSTIC_DSP.md)**: Pure math across Windows, Pi, MP3, and mic; hardware branches isolated to `hardware/`.

---

## 📖 Central Documentation

All documentation is hierarchically classified into the [5-Tier Documentation Authority Matrix](./docs/README.md):
- **[Documentation Portal](./docs/README.md)**: Central table of contents.
- **[System Architecture Blueprints](./docs/architecture/system_overview.md)**: Deep dive into the audio pipeline, rhythm tracker, transition director, and hardware abstraction.
- **[Reference Catalogs & Schemas](./docs/reference/modes_catalog.md)**: Complete catalog of the 22 active mounted visual modes, configuration schemas, and coordinate matrices.
- **[Operational Manuals](./docs/manuals/mode_authoring_guide.md)**: Step-by-step guides for authoring modes, Raspberry Pi deployment, developer tools, and the web interface.
- **[AI Agent Onboarding](./project_overview.md)**: Primary router for AI agents working in this repository.
