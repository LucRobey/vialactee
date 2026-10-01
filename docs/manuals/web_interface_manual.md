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

### A. Live Deck
- **Playlist & Preset Switcher:** Select active playlist or trigger immediate configuration changes.
- **Audio Reactivity Sliders:**
  - **Luminosity:** Master brightness (0–100%).
  - **Sensibility:** Audio gain threshold (1–100%).
- **Manual Triggers:**
  - **DROP:** Forces an instant structural music drop animation.
  - **Transition Type & Duration:** Selects transition algorithm (`fade_in_out`, `curtain`, `wave`, `explosion`) and duration in seconds.

### B. Topology Designer
- **2D Patchbay:** Displays interactive visual layout of all chandelier segments and patch cables dynamically loaded from `GET /api/topology`.
- **LIVE Mode:** Clicking a segment allows immediately overriding its active visual mode and direction.
- **MODIFY / BUILD Modes:** Allows editing presets and saving them permanently to `data/configurations_*.json` via `POST /api/configurations`.

### C. Mode Settings
- Dynamically generates interactive UI sliders and color pickers for any custom parameters declared in `Mode.get_settings_schema()`.
- Updates are saved per-preset and synced over WebSocket.
