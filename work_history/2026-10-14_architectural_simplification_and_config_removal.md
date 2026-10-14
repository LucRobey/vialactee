# [2026-10-14] Architectural Simplification, 4-Scene Migration, and Configuration/Playlist Removal

> **Date:** 2026-10-14  
> **Session ID:** `96fb2146-f004-4467-a6ca-e2ef22723b8f`  
> **Agent / Model:** Antigravity  
> **Primary Goal:** Execute the 5-step architectural simplification plan (DSP dead-code removal, 4-scene migration, `Segment.py` caching & transition deduplication, staggered auto-transitions) and completely remove all legacy preset/playlist/configuration systems across backend, frontend, and documentation.  
> **Status:** COMPLETED  
> **Commits:** `d67846c` `28d79dc` (pushed: yes)  
> **Skills Used:** `vialactee-project`  
> **Skill Friction:** none

---

## 1. Context & Motivation

* Following the sealed-sector isolation of `transitions/` and `mood/` and the 3-tier Musical Context Engine upgrade, several legacy layers remained across the codebase:
  1. Dead DSP fields (`band_peak` in `AudioIngestion`, unused `BeatGridQuantizer.py`).
  2. Dual 6-regime (`regime`, `regime_name`, `is_drop_buildup`) + 4-scene (`scene`, `scene_name`) representations in `MusicalContextEngine`, `mood/`, `transitions/`, and developer tools.
  3. Redundant mode registry reads and duplicated transition blending math inside `core/Segment.py`.
  4. Unwired cohort staggering on automatic transitions (`timer`, `song_change`, `structural_change`).
  5. Legacy configuration/playlist/preset files (`data/configurations*.json`, `Data_reader.py`), HTTP routes (`/api/configurations`), WebSocket commands (`select_playlist_slot`, `build_configuration`, `modify_configuration`), state dicts (`Mode_master.activ_configuration`), and React configurator components (`Configurator.tsx`, `TopologyConfigurationPanel.tsx`, `TopologyPlaylistPanel.tsx`, `configurationStore.ts`).

---

## 2. Changes Made

### 1. Core Audio & Context Simplification
* **[DELETE]** `core/BeatGridQuantizer.py`: Removed unused beat-grid quantizer module.
* **[MODIFY]** [`core/AudioIngestion.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AudioIngestion.py), [`core/Listener.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Listener.py), [`modes/Shining_stars_mode.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/modes/Shining_stars_mode.py): Removed dead `band_peak` buffer and references.
* **[MODIFY]** [`core/MusicalContextEngine.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/MusicalContextEngine.py), [`mood/scene_policy.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/mood/scene_policy.py), [`transitions/api.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/api.py), [`transitions/director.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/director.py), [`transitions/manager.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/manager.py), [`core/TransitionBridge.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/TransitionBridge.py), [`tools/mode_studio.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tools/mode_studio.py), [`tools/music_studio.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/tools/music_studio.py): Dropped the legacy 6-regime state machine (`RegimeId`, `regime`, `regime_name`, `is_drop_buildup`, `sustained_high_flux_frames`, `high_salience_frames`) and standardized on the 4-scene taxonomy (`CHILL = 0`, `GROOVE = 1`, `BUILDUP = 2`, `DROP_IMPACT = 3`).

### 2. Segment Caching, Transition Engine Deduplication & Staggered Auto-Transitions
* **[MODIFY]** [`core/Segment.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Segment.py), [`transitions/engine.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/engine.py): Added class-level `_MODES_CLASS_CACHE` in `Segment` so `config/modes.json` is loaded and imported once per process; unified transition buffer blending through `TransitionEngine.blend_into()` with zero hot-path allocation.
* **[MODIFY]** [`transitions/service.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/service.py), [`transitions/stagger.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/transitions/stagger.py): Enabled cohort staggering (`STAGGERED_AUTO_REASONS = frozenset({"timer", "song_change", "structural_change"})`) for automatic transitions while keeping drop triggers (`pre_drop_buildup`, `drop_impact`) and manual actions simultaneous.

### 3. Complete Removal of Configurations, Playlists & Presets
* **[DELETE]** `data/configurations.json`, `data/configurations_full.json`, `data/configurations_small.json`, `data/Data_reader.py`.
* **[RENAME / MODIFY]** `core/PresetRepository.py` $\to$ [`core/AppConfigStore.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/AppConfigStore.py) (`AppConfigStore`), [`config/Configuration_manager.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/config/Configuration_manager.py): Removed `resolve_configurations_file_path` and renamed the debounced `app_config.json` writer to `AppConfigStore`.
* **[MODIFY]** [`core/Mode_master.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/Mode_master.py), [`core/CommandRouter.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/CommandRouter.py), [`connectors/Connector.py`](file:///c:/Users/Users/Desktop/vialactée/vialactee/connectors/Connector.py): Replaced `self.activ_configuration` with `self.mode_settings`, renamed `initiate_modes()` and `_persist_mode_settings()`, removed playlist/configuration keys from `get_state_snapshot()`, removed `/api/configurations` HTTP routes, and removed `select_playlist_slot`, `build_configuration`, and `modify_configuration` WebSocket commands.
* **[DELETE / MODIFY]** [`wabb-interface/src/components/pages/TopologyEditor.tsx`](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/components/pages/TopologyEditor.tsx), [`wabb-interface/src/utils/controlBridge.ts`](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/utils/controlBridge.ts), [`wabb-interface/src/components/pages/LiveDeck.tsx`](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/src/components/pages/LiveDeck.tsx), [`wabb-interface/vite.config.ts`](file:///c:/Users/Users/Desktop/vialactée/vialactee/wabb-interface/vite.config.ts): Deleted `Configurator.tsx`, `configurationStore.ts`, and 5 topology configuration/playlist components; simplified `TopologyEditor.tsx` from 734 lines to 214 lines as a pure live segment mode/direction inspector.

### 4. Documentation Alignment
* **[DELETE]** `docs/architecture/transition_director.md` (consolidated into [`docs/reference/transition_contract.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/transition_contract.md)).
* **[MODIFY]** Updated [`docs/architecture/musical_context_engine.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/architecture/musical_context_engine.md), [`docs/reference/mood_contract.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/mood_contract.md), [`docs/reference/transition_contract.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/transition_contract.md), [`docs/architecture/api_and_wire_protocol.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/architecture/api_and_wire_protocol.md), [`docs/reference/configuration_schemas.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/docs/reference/configuration_schemas.md), [`core/precisions/mode_master.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/precisions/mode_master.md), [`core/precisions/segment.md`](file:///c:/Users/Users/Desktop/vialactée/vialactee/core/precisions/segment.md), and module READMEs.

---

## 3. Verification & Testing

* **Command**: `python -m pytest tests/test_app_config_store.py tests/test_mode_master_snapshot.py tests/test_transition_bridge.py tests/governance tests/test_docs_parity_and_bugs.py -q --no-header -p no:cacheprovider`
  * **Result**: `51 passed in 9.15s`.
* **Command**: `python -m pytest tests/test_musical_context_engine.py tests/test_segment.py tests/transitions -q --no-header -p no:cacheprovider`
  * **Result**: All context engine, segment caching/blending, and transition service/stagger tests passed.

---

## 4. Architecture Decisions & Trade-offs

* **Single 4-Scene Taxonomy**: Eliminated the parallel 6-regime system (`CALM_AMBIENT`..`BREAKDOWN_PAUSE`) so `MusicalContextEngine`, `mood/`, `transitions/`, and modes speak a single 4-scene vocabulary (`CHILL`, `GROOVE`, `BUILDUP`, `DROP_IMPACT`).
* **Pure Live Random DNA + Persisted `mode_settings`**: With presets and playlists removed, `Mode_master` holds only `self.mode_settings: Dict[str, Dict[str, Any]]` persisted via `AppConfigStore` to `config/app_config.json`, while live segment allocations live directly on the `Segment` instances.

---

## 5. Pitfalls & Lessons Learned

* Keep documentation and governance tests (`tests/governance/test_axiom_03_geometry.py`, `tests/governance/test_axiom_07_code_governance.py`, `tests/test_code_governance.py`) updated in lockstep when deleting legacy data files (`data/configurations*.json`) or modules (`BeatGridQuantizer.py`).

---

## 6. Open Items & Next Steps

* None — all 5 simplification phases and configuration/playlist removals are complete.
