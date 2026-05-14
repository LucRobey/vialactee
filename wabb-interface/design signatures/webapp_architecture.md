# Wabb-Interface: UI/UX Architecture

> **IMPLEMENTATION STATUS:**
> | Page | Status | Description |
> |---|---|---|
> | 📱 1. Live Deck | ✅ Implemented | Core performance UI (Playlists, Luminosity / Sensibility / Auto-Transition sliders, transitions, manual drop) |
> | 📐 2. Topology | ✅ Implemented | LIVE spatial map mirroring `mode_master_state` with per-segment inspector |
> | 🧱 3. Configurator | ✅ Implemented | MODIFY / BUILD preset authoring built on the same topology canvas |
> | 🎛️ 4. Mode Settings | ✅ Implemented | Per-mode tuning with runtime application |
> | ⚙️ 5. System & Setup | ✅ Implemented | Telemetry stream and hardware danger-zone actions |

This document outlines the structural layout and user experience philosophy for the Vialactée Web Interface. To ensure safety during live performances and to prevent accidental configuration changes, the interface is split into **five distinct pages**, navigated via a persistent top tab bar (`App.tsx`).

## 📱 Page 1: The Live Deck (Performance Mode)
*Philosophy: High-stress live operation. Massive touch targets, read-only monitoring, and macro controls only.*

**Components (implemented in `components/pages/LiveDeck.tsx`):**
*   **Telemetry strip:** CPU temperature, active playlist, active configuration, and dynamic audio latency hydrated from `mode_master_state` / `state.system`. No local placeholder values.
*   **Playlist Presets:** Up to eight thumb-friendly bricks generated only from the playlists exposed by `data/configurations.json` and `mode_master_state.playlists`. The UI never seeds fallback or demo playlist names.
*   **Macro Sliders (left column):** Three vertical Lego sliders:
    *   *Luminosité* (1 → 100) — `set_luminosity`
    *   *Sensibilité* (1 → 100) — `set_sensibility`
    *   *Auto Trans (S)* (5 → 300 seconds) — `set_auto_transition_time`
*   **Next Configuration + Next Transition queue:** Two flat dropdowns mounted on the central orange baseplate. The Next Configuration row exposes a round blue baton-pass button that fires `go_to_next_configuration` with the queued configuration and selected transition (`CUT`, `FADE IN/OUT`, or `CROSSFADE`).
*   **HOLD / LIVE switch:** Heavy-duty toggle that calls `lock_current_configuration`; it also drives the perimeter glow on the orange baseplate (green for LIVE, red for HOLD).
*   **The DROP Button:** The visual focal point of the deck. A massive button constructed from physical 1x1 tiles that emits a `manual_drop` instruction (music-drop style override).

---

## 📐 Page 2: Topology (LIVE map + inspector)
*Philosophy: Show what the chandelier is doing right now and let the operator nudge a single segment without touching the saved JSON.*

**Components (shared `TopologyEditor.tsx` rendered with `allowedModes={['LIVE']}`):**
*   **Segment map:** Fixed stud grid with selectable segments (modes shown on tiles); junction boxes at intersections.
*   **Dynamic inspector:** Mode tiles for the selected segment (list comes from `mode_master_state.availableModes`).
*   **Hidden in this tab:** Because `allowedModes` is locked to `LIVE`, the `TopologyEditorModeSwitch`, `TopologyConfigurationPanel`, and `TopologyPlaylistPanel` are not rendered — preset authoring lives in the Configurator tab.
*   **Behavior:** Follows `mode_master_state` over `/ws`. Mode and direction changes go out as WebSocket instructions (`select_segment_mode`, `toggle_segment_direction`) and affect the running Python segments only, not the JSON file. The client keeps **pending** mode/direction per segment until the snapshot matches, avoiding flicker from ~30 Hz updates.

---

## 🧱 Page 3: Configurator (preset authoring)
*Philosophy: Same topology canvas as Page 2, but its only job is to author the playlists / configurations stored on disk.*

**Components (`components/pages/Configurator.tsx` reuses `TopologyEditor` with `allowedModes={['MODIFY', 'BUILD']}` and `syncPlaylistsFromModeMaster=false`):**
*   Full topology map + segment inspector for editing modes / directions locally.
*   `TopologyEditorModeSwitch` toggles between `MODIFY` and `BUILD` (no `LIVE` here).
*   `TopologyConfigurationPanel` — configuration selector, name field, rename / delete / save controls.
*   `TopologyPlaylistPanel` — playlist name draft + create / rename / delete / cycle (`select_playlist_slot`).
*   **MODIFY:** Save overwrites the selected configuration. After a successful `POST /api/configurations`, the UI emits `modify_configuration` so `Mode_master` reloads from disk.
*   **BUILD:** Save can append a new configuration or, with confirm-overwrite, replace an existing one. The UI emits `build_configuration` after the disk write.
*   Configuration JSON is loaded from the bundled raw file via `loadConfigurationFileStore`, so the Configurator does not race the live `mode_master_state` snapshots.

---

## 🎛️ Page 4: Mode Settings (Per-Mode Tuning)
*Philosophy: Tuning the mathematical feel of each visual mode during soundcheck while keeping the active configuration as the persistence boundary.*

**Components (`components/pages/ModeSettings.tsx`):**
*   **Dynamic Mode Catalog:** Every mode that exposes at least one setting via `mode_master_state.modeSettingsCatalog` appears automatically.
*   **Per-Mode Cards:** Each card renders one or more controls inherent to that mode.
*   **Supported Controls:** `switch`, `slider`, and `list`, all driven by backend-provided descriptors rather than hardcoded React JSX.
*   **Live Runtime Apply:** Adjustments go out over `/ws` as `set_mode_setting` instructions, are validated by `Mode_master`, and immediately affect every live segment instance currently using that mode.
*   **Pending merge:** Pending values are kept on the client until the next snapshot reports a matching value, preventing flicker as ~30 Hz updates arrive.
*   **Configuration Persistence:** The active configuration owns the `modeSettings` values, so Configurator saves carry their own tuning.

---

## ⚙️ Page 5: System & Setup (Admin Mode)
*Philosophy: Hardware health monitoring and ultimate control. Rarely visited during an active show, purely diagnostic and dangerous.*

**Components (`components/pages/SystemSetup.tsx`):**
*   **Live Telemetry from `state.system`:** Pi CPU temperature, RAM and disk usage, Python loop FPS / health, simulation vs Pi hardware mode, ESP32 reachability, phone Bluetooth status, microphone state, audio stream state / health, last sample age, dynamic latency, uptime, hostname / platform, connected web-client count.
*   **Hardware Management (Danger Zone):** `RESTART PYTHON LOOP` and `REBOOT RASPBERRY PI`, both gated by the `system.actions` capability flags from the backend; the UI surfaces the last action feedback (pending / success / error) and disables buttons when the bridge is offline.

## Data And State Rules

* `data/configurations.json` is the single source of truth for playlists and saved configurations.
* `src/utils/configurationStore.ts` is the React load/save boundary for that JSON file (HTTP for Live Deck/Topology, bundled raw file for Configurator).
* `/api/configurations` is implemented both by Vite during local development and by `connectors/Connector.py` when Python serves the backend.
* `/ws` remains the live control channel. The browser sends page/action instructions and receives `mode_master_state` snapshots describing the active playlist, active/queued configuration, transition state, luminosity, sensibility, auto-transition time, current segment modes/directions, the mode-settings catalog and effective `modeSettings`, plus the `system` telemetry block. Topology in `LIVE` treats those snapshots as authoritative once they agree with any pending user override for a segment.
