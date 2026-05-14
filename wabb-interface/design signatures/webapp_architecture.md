# Wabb-Interface: UI/UX Architecture

> **IMPLEMENTATION STATUS:**
> | Page | Status | Description |
> |---|---|---|
> | 📱 1. Live Deck | ✅ Implemented | Core performance UI (Playlists, Speed/Brightness, Transitions) |
> | 📐 2. Topology Editor | ✅ Implemented | Visual map for live overrides and preset building |
> | 🎛️ 3. Mode Settings | ✅ Implemented | Per-mode tuning with runtime application |
> | ⚙️ 4. System & Setup | ❌ Planned | Telemetry and hardware danger-zone |

This document outlines the structural layout and user experience philosophy for the new Vialactée Web Interface. To ensure safety during live performances and to prevent accidental configuration changes, the interface is split into **four distinct pages**, navigated via a persistent top or bottom tab bar.

## 📱 Page 1: The Live Deck (Performance Mode)
*Philosophy: High-stress live operation. Massive touch targets, read-only monitoring, and macro controls only.*

**Components:**
*   **Stage Overview:** A simplified, non-interactive, read-only SVG map that purely mirrors what the physical LEDs are doing.
*   **Playlist Presets:** A grid of massive, thumb-friendly buttons generated only from the playlists saved in `data/configurations.json`. The UI must not contain fallback or demo playlist names.
*   **Macro Sliders:** Two large, high-contrast sliders:
    *   *Master Speed Multiplier* (0.1x to 3.0x)
    *   *Master Brightness* (0% to 100%)
*   **Auto-DJ Toggle:** A simple ON/OFF switch to engage the automatic transition engine.
*   **The DROP Button:** The focal point of the deck. A massive button that executes the queued saved configuration with the selected transition.

---

## 📐 Page 2: Topology Editor (map + inspector)
*Philosophy: See the chandelier layout, pick a segment, and either mirror the live show or edit saved presets.*

**Components (implemented in `TopologyEditor.tsx`):**
*   **Segment map:** Fixed stud grid with selectable segments (modes shown on tiles); junction boxes at intersections.
*   **Dynamic inspector:** Mode tiles for the selected segment, configuration name area, playlist strip, three-way **LIVE / MODIFY / BUILD** switch.
*   **`LIVE`:** Follows `mode_master_state` over `/ws`. Mode and direction changes go out as WebSocket instructions (`select_segment_mode`, `toggle_segment_direction`) and affect the running Python segments only, not the JSON file. The client keeps **pending** mode/direction per segment until the snapshot matches, avoiding flicker from ~30 Hz updates. Switching **LIVE → MODIFY** reapplies the selected saved configuration from the React store so edits target disk-backed presets.
*   **`MODIFY` / `BUILD`:** Authoring modes; saving uses `POST /api/configurations` and notifies `Mode_master` to reload.

---

## 🎛️ Page 3: Mode Settings (Per-Mode Tuning)
*Philosophy: Tuning the mathematical feel of each visual mode during soundcheck while keeping the active configuration as the persistence boundary.*

**Components:**
*   **Dynamic Mode Catalog:** Every loaded mode that exposes at least one setting appears automatically.
*   **Per-Mode Cards:** Each card renders one or more controls that are inherent to that mode.
*   **Supported Controls:** `switch`, `slider`, and `list`, all driven from backend-provided descriptors rather than hardcoded React JSX.
*   **Live Runtime Apply:** Adjustments go out over `/ws`, are validated by `Mode_master`, and immediately affect every live segment instance currently using that mode.
*   **Configuration Persistence:** The active configuration owns the `modeSettings` values, so saved presets carry their own tuning.

---

## ⚙️ Page 4: System & Setup (Admin Mode)
*Philosophy: Hardware health monitoring and ultimate control. Rarely visited during an active show, purely diagnostic and dangerous.*

**Components:**
*   **Live Telemetry:** Clean readouts for critical hardware health: Pi CPU Temperature, Python Loop FPS, and RAM usage.
*   **Hardware Management (Danger Zone):**
    *   Master Power Limit Slider (Capping RGB values).
    *   `RESTART PYTHON LOOP` button.
    *   `REBOOT RASPBERRY PI` button.

## Data And State Rules

* `data/configurations.json` is the single source of truth for playlists and saved configurations.
* `src/utils/configurationStore.ts` is the React load/save boundary for that JSON file.
* `/api/configurations` is implemented both by Vite during local development and by `connectors/Connector.py` when Python serves the backend.
* `/ws` remains the live control channel. The browser sends page/action instructions and receives `mode_master_state` snapshots describing the active playlist, active/queued configuration, transition state, luminosity, sensibility, current segment modes/directions, the mode-settings catalog, and the active configuration's effective `modeSettings`. Topology in `LIVE` treats those snapshots as authoritative once they agree with any pending user override for a segment.
