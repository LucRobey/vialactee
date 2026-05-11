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
*   **Configuration Saving:** BUILD/MODIFY writes the current segment mode/direction map back into `data/configurations.json` through `/api/configurations`. Saved playlists and configurations become available to Live Deck after the backend reloads and broadcasts a fresh state snapshot.

---

## 📐 Page 3: Topology Layout Editor (Stage Setup)
*Philosophy: Defining the physical layout of the environment. Used during initial stage construction to ensure accurate visual representations.*

**Components:**
*   **Interactive Grid:** A canvas where the user can drag, scale, and rotate the physical SVG segments to match how the real-world stage was built that day.
*   **Coordinate Sync:** Automatically saves the updated X/Y coordinates back to the Pi to ensure spatial transitions sweep correctly across the real space.

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
* `/ws` remains the live control channel. The browser sends page/action instructions and receives `mode_master_state` snapshots describing the active playlist, active/queued configuration, transition state, luminosity, sensibility, and current segment modes/directions.
