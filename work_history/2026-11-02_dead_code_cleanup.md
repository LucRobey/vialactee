# [2026-11-02] Dead Code Hunt Audit & Tier 1 Repository Cleanup

> **Date:** 2026-11-02  
> **Session ID:** `f5bace25-cfd0-4e5a-a945-9d71e136cb95`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Audit the Dead Code Hunt Report against sealed-room contracts and `research/`, and execute Tier 1 git index & orphaned artifact cleanup.  
> **Status:** IN PROGRESS  
> **Commits:** `8130bb5`, `1e05ad4` (pushed: yes)  
> **Skills Used:** `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* Reviewed the comprehensive Dead Code Hunt Report across `Main.py`, `core/`, `config/`, `connectors/`, `hardware/`, `modes/`, `mood/`, `music/`, `utils/`, `tools/`, `scripts/`, `tests/`, and root-level files.
* Cross-checked the report against excluded directories (`research/`, `transitions/`, `wabb-interface/`), sealed-room contracts (`docs/contracts/`), and governance tests (`tests/governance/test_docs_parity.py`).
* Executed Phase 1 (Tier 1: Orphaned Files & Stale Git-Tracked Artifacts).

---

## 2. Changes Made

### Tier 1: Git Index, Stale Bytecode, Tracked Caches & Secrets Cleanup
* **[MODIFY]** [`.gitignore`](../.gitignore):
  * Added `hardware/esp32_firmware/**/secrets.h` so local ESP32 Wi-Fi credentials remain untracked while `secrets.h.example` templates stay tracked.
* **[DELETE]** `.cursor/debug-3844d0.log`, `.cursor/debug-c929ba.log`, `.cursor/debug-fac19c.log`:
  * Removed stale tracked debug logs via `git rm -f`.
* **[DELETE]** `generate_pdf.py` & `Vialactee_Project_Overview.pdf`:
  * Removed unreferenced standalone PDF generator script and generated PDF from repository root via `git rm -f`.
* **[DELETE]** `hardware/esp32_firmware/secrets.h` & `hardware/esp32_firmware/secrets.h.example`:
  * Deleted unused parent-level `secrets.h*` files via `git rm -f` and untracked `hardware/esp32_firmware/ESP32_full/secrets.h` and `hardware/esp32_firmware/ESP32_small/secrets.h` via `git rm --cached` (keeping local files on disk).
* **[DELETE]** Stale tracked & orphaned bytecode and cache dumps:
  * Untracked 14 `.pyc` files in `__pycache__/`, `data/__pycache__/`, and `modes/__pycache__/` via `git rm --cached`, and removed the empty `data/` ghost directory and orphaned `.pyc` files in `tests/__pycache__/`.
  * Untracked 14 `assets/musics/mp3_files/librosa/*.npz` cache files via `git rm --cached`.

### Phase 3 (Part A): Obsolete `has_custom_transition`, Core/Config Helpers & Tier 4 Legacy Fallbacks
* **[MODIFY]** [`modes/Mode.py`](../modes/Mode.py), [`core/Segment.py`](../core/Segment.py) & [`docs/architecture/core_orchestrator.md`](../docs/architecture/core_orchestrator.md):
  * Removed obsolete `self.has_custom_transition = False` and `has_custom` branch checks in `Segment.update()`, relying solely on `self.transition_mode_handshake` (`TransitionFamily.MODE_COOPERATIVE`).
  * Removed unused `Segment.export_mode_settings()` and camelCase duplicate `Segment.unBlock()`, updating `Segment.unblock()` to set `self.isBlocked = False` directly.
* **[MODIFY]** [`core/AppConfigStore.py`](../core/AppConfigStore.py):
  * Removed unused `async def persist_app_config_value()` and write-only `self._pending_app_config_updates` dictionary.
* **[MODIFY]** [`config/coherence_loader.py`](../config/coherence_loader.py) & [`config/Configuration_manager.py`](../config/Configuration_manager.py):
  * Removed unused `MODES_CONFIG_PATH`, `COHERENCE_LEGACY_PATH` (`"coherence.json"`), and `"segments.json"` fallback (plus matching fallback in [`wabb-interface/vite.config.ts`](../wabb-interface/vite.config.ts)).
* **[MODIFY]** [`connectors/Connector.py`](../connectors/Connector.py):
  * Removed legacy `web/` static directory fallback in `resolve_web_dir()`.
* **[MODIFY]** 6 Mode Constructors (`modes/*_mode.py`), [`tests/test_mode_render.py`](../tests/test_mode_render.py) & [`tools/mode_studio.py`](../tools/mode_studio.py):
  * Removed nested legacy unprefixed `infos.get(...)` fallbacks in `Chromatic_chaser_mode`, `Hyper_strobe_mode`, `Metronome_mode`, `Opposite_sides_mode`, `Rainbow_mode`, and `Shining_stars_mode`, standardizing on the documented prefixed startup keys (`chaser_*`, `strobe_*`, `metronome_*`, `opposite_sides_*`, `rainbow_*`, `stars_*`).
  * Updated `tests/test_mode_render.py` to pass `stars_*` startup keys and removed stale `{"shot_base_speed": 2.0}` in `tools/mode_studio.py`.

---

## 3. Verification & Testing

* **Command**: `.\.venv\Scripts\python.exe -m pytest -q`
  * **Result**: `558 passed, 5 deselected, 127 subtests passed in 38.26s`.

---

## 4. Architecture Decisions & Trade-offs

* **Decision 1 (Contract & Research Safeguards)**: Identified that `comb_kernels.py` (`hann`, `boxcar`), `Listener` / `MusicalContextEngine` properties (`dynamic_audio_latency`, `standalone_bpm`, `standalone_phase`, `live_salience`, `live_asserved_total_power`, etc.), `MoodService.next_palette` / `set_auto_scene`, and `Mode.palette_sample` are either actively used in `research/` or governed by Tier-1 sealed-room contracts (`docs/contracts/`) and `test_docs_parity.py`.
* **Decision 2 (Non-Destructive Un-tracking)**: Used `git rm --cached` for `ESP32_full/secrets.h`, `ESP32_small/secrets.h`, and `assets/musics/mp3_files/librosa/*.npz` so local developer Wi-Fi credentials and precomputed librosa caches remain intact on disk while being purged from the git index.

---

## 5. Pitfalls & Lessons Learned

* Always cross-check static dead-code reports against excluded directories (`research/`) and contract parity tests (`tests/governance/test_docs_parity.py`) before deleting public properties or kernel options.

---

## 6. Open Items & Next Steps

* [ ] Phase 2 (Tier 3): Fix broken paths in `tools/eval_skills.py`, remove unreachable duplicate block in `tools/structural_annotator.py`, fix duplicate `<FastLED.h>` include in `ESP32_small.ino`, strip UTF-8 BOM in `tests/test_coherence_helper_build.py`, and clean write-only state & unused imports.
* [ ] Phase 3 (Tiers 2 & 4): Remove unreferenced non-contract helpers, wire `RhythmConfig.structural_warmup_frames`, and remove legacy config/path fallbacks.
* [ ] Phase 4 (Tier 5.1): Retire legacy in-process `Fake_leds` wrapper and module-level `visualizer = FakeLedsVisualizer()` singleton.
