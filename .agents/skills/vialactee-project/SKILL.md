---
name: vialactee-project
description: Central knowledge, architecture boundaries, and execution rules for the Vialactée interactive LED chandelier project. Use when modifying core orchestration, coordinating multiple domains, or onboarding to the codebase.
---

# Vialactée Project & Architecture Master Skill

Use this skill as the primary architectural authority for the Vialactée music-reactive LED chandelier repository. It defines global system invariants, threading models, and indexes the specialized domain skills.

---

## 1. Directory Structure

* `Main.py`: The asynchronous orchestration entry point.
* `transitions/`: `transitions/` is a sealed room: all transition logic lives there and is reached only through `transitions.api` (see `docs/reference/transition_contract.md`). Enforced by `tests/governance/test_transition_isolation.py`; to work on it alone run `python -m transitions.sandbox`.
* `mood/`: `mood/` is a sealed room (curated palettes, cosine crossfade, scene rules) reached only through `mood.api` (see `docs/reference/mood_contract.md`). Enforced by `tests/governance/test_mood_isolation.py`. Modes read colours via `Mode.mood_colors`, bound by `Mode_master`.
* `core/`: The math and execution engine (`Mode_master.py`, `CommandRouter.py`, `AppConfigStore.py`, `TransitionBridge.py`, `Listener.py`, `MusicalContextEngine.py`, `AudioAnalyzer.py`, `AudioIngestion.py`, `Segment.py`).
* `modes/`: Visual light animation modes inheriting from `modes.Mode`.
* `config/`: Hardware profiles (`hardware_profile` in `app_config.json`), unified physical geometry + UI layout (`segments_full.json`, `segments_small.json`), and dynamic path resolution (`Configuration_manager.py`).
* `hardware/`: Physical abstractions (`Fake_leds.py`, `Rpi_NeoPixels.py`, `Udp_Sender.py`, `HardwareFactory.py`, `Fake_ESP32.py`).
* `connectors/`: Asynchronous integrations (`Connector.py` aiohttp server exposing `/ws` and `/api/topology`, plus `Local_Microphone.py`).
* `wabb-interface/`: React-based remote control web interface.
* `research/`: Offline MIR laboratory, synthetic/neural/academic benchmark harnesses, and experimental algorithm ledger.
* `work_history/`: Permanent chronological session logs (`work_history/README.md`, `work_history/TEMPLATE.md`) to maintain persistent engineering context and avoid agent amnesia.
* `docs/`: Master documentation root (The 9 Golden Axioms in `docs/axioms/`, Architecture Specs in `docs/architecture/`, Catalogs in `docs/reference/`, Manuals in `docs/manuals/`).

---

## 2. Core System Invariants

### 1. Hardware Profiles (`full` vs `small`)
* **`full` (Default)**: 1,304 LEDs across 11 segments on 2 channels (`segs_1`: 785 LEDs, `segs_2`: 519 LEDs). Uses `segments_full.json`.
* **`small`**: 249 LEDs across 3 segments on 1 channel (`segs_1`: `s1` 49, `s2` 108, `s3` 92). Uses `segments_small.json`.
* **Path Resolution**: Never hardcode file paths for segments. Always use `Configuration_manager.resolve_segments_file_path(infos)`.

### 2. PyGame Threading on Windows
PyGame is strictly bound to the **main thread** on Windows.
Whenever invoking `.show()` in `Mode_master.py`, always check `infos.get("onRaspberry")`:
* If `True` (Raspberry Pi): Use `loop.run_in_executor` to offload `neopixel.show()` and prevent `asyncio` loop stalls.
* If `False` (Windows Sim): Call `.show()` synchronously in the main thread to prevent "Not Responding" OS freezes.

### 3. Physical LED Wiring & Orientation
* **Full Profile**: Total LEDs: **1,304** across 11 segments.
* **Vertical Invariant**: Physical vertical LED strips (`v1`, `v2`, `v3`, `v4`) are wired **bottom-to-top**. In `Fake_leds.py`, their orientation is `"vertical_up"`, `y -= 2`, and `start_y` corresponds to their bottom-most coordinate.

### 4. Dev Server Port Collision Prevention
In local testing on Windows, `Main.py` sets `infos["startServer"] = False` by default to prevent socket collision crashes on `0.0.0.0:8080` during successive `Ctrl+C` restarts. Set `startServer: True` only when explicitly testing web connectors.

### 5. Code Style & Aliased Imports
Preserve existing aliased import conventions:
```python
import core.Mode_master as Mode_master
import hardware.Fake_leds as Fake_leds
```

### 6. Agent Work History Protocol
Every engineering or research session that creates, deletes, or modifies files or configurations must:
1. Create a dated markdown log in `work_history/` (following `work_history/TEMPLATE.md`).
2. Add an entry to the chronological table in `work_history/README.md`.
3. Document exact verification steps, test pass counts, and any open follow-ups.

### 7. Commit & Push Protocol
Git history is the second half of the project's memory (`work_history/` explains *why*, git shows *what*). Keep both in sync:
1. **Start of session:** run `git status` and `git log --oneline -n 10`. If the tree is dirty with work that is not yours, tell the user before touching anything.
2. **Commit per logical step**, not per session. Use Conventional Commits: `type(scope): summary`.
   * Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
   * Scopes: `dsp`, `transitions`, `mood`, `modes`, `web`, `hardware`, `research`, `docs`.
   * Multi-step efforts put the step in the message, e.g. `refactor(mood): phase 2 - ...`.
3. **Test before committing:** run `python -m pytest -q`. Never commit with failing tests unless the commit message says `wip`.
4. **Commit the session log with the code** (same commit, or a final `docs(history): ...` commit). Then add the hash(es) to the log's `Commits` field.
5. **Push** at the end of every session and after every completed phase or feature: `git push`.
6. **Never** use `git push --force`, `git reset --hard`, or `git add -A` blindly. Stage files explicitly and check that no logs, caches or scratch files slip in.

---

## 3. Specialized Domain Skills & Subsystem Authority Index

For specialized development domains, refer to the dedicated workspace skills:

| Domain | Skill Name | Location & Purpose |
|---|---|---|
| **Visual Modes** | `vialactee-mode-creator` | [`.agents/skills/vialactee-mode-creator/SKILL.md`](../vialactee-mode-creator/SKILL.md) — Vectorized rendering, `Mode` subclassing, 30 FPS budget, dynamic settings schemas. |
| **DSP & Beat Tracking** | `vialactee-dsp-engine` | [`.agents/skills/vialactee-dsp-engine/SKILL.md`](../vialactee-dsp-engine/SKILL.md) — Mel/chroma matrices, Anticipation Flywheel ("Oracle"), 60 Hz tick budget, 3-tier Musical Context Engine. |
| **Strategic Research Director** | `vialactee-research-manager` | [`.agents/skills/vialactee-research-manager/SKILL.md`](../vialactee-research-manager/SKILL.md) — Cross-domain ideation, living idea tree, anti-incremental gate, research briefings. |
| **Tactical Research Worker** | `vialactee-researcher` | [`.agents/skills/vialactee-researcher/SKILL.md`](../vialactee-researcher/SKILL.md) — Model implementation, 10-track `neural-core` benchmarks, ablation, failure diagnostics. |

For subsystems governed directly by canonical documentation and unit tests:
* **Transitions (Sealed Room):** [`docs/reference/transition_contract.md`](../../../docs/reference/transition_contract.md) and [`transitions/api.py`](../../../transitions/api.py) (verified by `tests/governance/test_transition_isolation.py`).
* **Mood (Sealed Room):** [`docs/reference/mood_contract.md`](../../../docs/reference/mood_contract.md) and [`mood/api.py`](../../../mood/api.py) (verified by `tests/governance/test_mood_isolation.py`).
* **Hardware & Deployment:** [`docs/manuals/raspberry_pi_deployment.md`](../../../docs/manuals/raspberry_pi_deployment.md) and [`docs/reference/coordinates_matrix.md`](../../../docs/reference/coordinates_matrix.md).
* **Web Remote Control:** [`docs/architecture/api_and_wire_protocol.md`](../../../docs/architecture/api_and_wire_protocol.md) and [`wabb-interface/DESIGN_SYSTEM.md`](../../../wabb-interface/DESIGN_SYSTEM.md).
