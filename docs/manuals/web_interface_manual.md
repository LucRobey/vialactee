# Web Interface Operator Manual (Wabb-Interface)

> **Location:** `docs/manuals/web_interface_manual.md` (Tier 2 Operational Manual)  
> **Source Directory:** [`wabb-interface/`](../../wabb-interface/)  
> **Backend Connector:** [`connectors/Connector.py`](../../connectors/Connector.py)

The **Wabb-Interface** is the web remote controller for the chandelier, built with React, Vite, and Tailwind CSS. It communicates with the Python backend via REST APIs and WebSocket (`ws://<ip>:8080/ws`).

---

## 1. Starting the Web Interface

### In Production (Pre-compiled Static Build)
When `startServer: true` in `config/app_config.json`, `Connector.py` automatically serves the pre-built frontend from `wabb-interface/dist/` on `http://<ip>:8080/`.

### In Development (Vite Dev Server)
To edit React components with hot module reloading:
```bash
cd wabb-interface
npm install
npm run dev
```
Open `http://localhost:5173/`. (Requires backend running on `:8080`).

---

## 2. Interface Pages & Controls

### A. Live Deck (`components/pages/LiveDeck.tsx`)
- **Mood Palette Bricks:** Select the active curated mood palette (`select_mood`), which smoothly crossfades across all segments via `mood.api`.
- **Transition Controls:**
  - **GO Button:** Triggers an immediate mode transition across non-blocked segments (`go_to_next_configuration`).
  - **HOLD / LIVE Switch:** Locks or unlocks automatic mode transitions (`lock_current_configuration`).
  - **DROP:** Forces an instant music-drop transition (`manual_drop`).
- **Master Override Sliders:**
  - **Luminosity:** Master brightness (1–100%, `set_luminosity`).
  - **Sensibility:** Audio sensitivity gain (1–100%, `set_sensibility`).
  - **Auto Trans (s):** Interval in seconds between automatic transitions (5–300 s, `set_auto_transition_time`).

### B. Topology (`components/pages/TopologyEditor.tsx`)
- **2D Patchbay:** Displays the interactive spatial layout of all chandelier segments and patch cables dynamically loaded from `GET /api/topology` (`config/segments_full.json` or `config/segments_small.json`).
- **Live Segment Inspector:** Clicking any segment lets the operator override its active visual mode (`select_segment_mode`) or toggle its animation direction (`toggle_segment_direction`) in real time.

### C. Mode Settings (`components/pages/ModeSettings.tsx`)
- Dynamically generates interactive UI sliders, switches, and dropdowns from `modeSettingsCatalog` (`Mode.get_settings_schema()`).
- Emits `set_mode_setting` over WebSocket, updating live segment instances immediately and persisting overrides to `mode_settings` in `config/app_config.json`.

### D. System (`components/pages/SystemSetup.tsx`)
- Displays live backend telemetry, active hardware profile (`FULL`: 2 Channels · 11 Segments, or `SMALL`: 1 Channel · 3 Segments), CPU temperature, and audio latency.
- Exposes host maintenance actions (`restart_python_loop`, `restart_raspberry_pi`) gated by backend capability flags.
