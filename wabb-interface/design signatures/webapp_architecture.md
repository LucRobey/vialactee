# Wabb-Interface: UI/UX Architecture

This document outlines the structural layout and user experience philosophy for the new Vialactée Web Interface. To ensure safety during live performances and to prevent accidental configuration changes, the interface is split into **five distinct pages**, navigated via a persistent top or bottom tab bar.

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

## 🗺️ Page 2: The Stage Architect (Deep Control)
*Philosophy: Dialing in specific looks, tweaking mathematical parameters, and staging complex batches. Used primarily during soundcheck or low-stress moments.*

**Components:**
*   **The Interactive Stage Mapper (Center):** The fully interactive SVG canvas. Tapping segments highlights them for editing; dragging allows multi-selection.
*   **The Dynamic Inspector (Sidebar):** Appears when a segment is selected on the canvas. Contains:
    *   **Segment Mode Dropdown:** Assigning a base mode (e.g., Pulsar, Rainbow).
    *   **Lock Toggle:** A switch to lock the segment, making it immune to Auto-DJ and Global Transitions.
    *   **Segment Mute:** Instantly blacks out the selected segment.
*   **Batch Execution:** A staged execution area where multiple segment changes sit in a "pending" state until an `EXECUTE STAGED BATCH` button is pressed.
*   **Configuration Saving:** `MODIFY` and `BUILD` write the current segment mode/direction map into `data/configurations.json` through `/api/configurations`. In `LIVE`, the save control does not persist (live tweaks are runtime-only). Saved playlists and configurations become available to Live Deck after the backend reloads and broadcasts a fresh state snapshot.

---

## 📐 Page 3: Topology Editor (map + inspector)
*Philosophy: See the chandelier layout, pick a segment, and either mirror the live show or edit saved presets.*

**Components (implemented in `TopologyEditor.tsx`):**
*   **Segment map:** Fixed stud grid with selectable segments (modes shown on tiles); junction boxes at intersections.
*   **Dynamic inspector:** Mode tiles for the selected segment, configuration name area, playlist strip, three-way **LIVE / MODIFY / BUILD** switch.
*   **`LIVE`:** Follows `mode_master_state` over `/ws`. Mode and direction changes go out as WebSocket instructions (`select_segment_mode`, `toggle_segment_direction`) and affect the running Python segments only, not the JSON file. The client keeps **pending** mode/direction per segment until the snapshot matches, avoiding flicker from ~30 Hz updates. Switching **LIVE → MODIFY** reapplies the selected saved configuration from the React store so edits target disk-backed presets.
*   **`MODIFY` / `BUILD`:** Authoring modes; saving uses `POST /api/configurations` and notifies `Mode_master` to reload.

---

## 🎛️ Page 4: Auto-DJ Tuning (Automation)
*Philosophy: Designing the rules of the autonomous light jockey. Configured during soundcheck to dictate how the system behaves when left alone.*

**Components:**
*   **Trigger Interval Slider:** Controls how often the system autonomously changes states (e.g., trigger every 5 minutes).
*   **Transition Sweep Duration Slider:** Controls the speed of the visual wipe across the room (e.g., transition takes 3 seconds).
*   **Mode Probabilities (Optional):** Weights defining which modes the Auto-DJ is more likely to select next.
*   **Mode Configuration Frame:** A dedicated section where every mode appears as a card. Each card contains the **Deep Parameters** for that specific mode (e.g., `Ball Size`, `Tail Length`, `Color Density`), presented as dynamic sliders mapped directly to the mode's internal global variables.

---

## ⚙️ Page 5: System & Setup (Admin Mode)
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
* `/ws` remains the live control channel. The browser sends page/action instructions and receives `mode_master_state` snapshots describing the active playlist, active/queued configuration, transition state, luminosity, sensibility, and current segment modes/directions. Topology in `LIVE` treats those snapshots as authoritative once they agree with any pending user override for a segment.
