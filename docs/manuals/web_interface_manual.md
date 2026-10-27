# Web Interface Operator Manual (Wabb-Interface)

> **Location:** `docs/manuals/web_interface_manual.md` (Tier 2 Operational Manual)  
> **Source Directory:** [`wabb-interface/`](../../wabb-interface/)  
> **Backend Connector:** [`connectors/Connector.py`](../../connectors/Connector.py)  
> **Wire Protocol:** [`docs/architecture/api_and_wire_protocol.md`](../architecture/api_and_wire_protocol.md)  
> **UI Design System:** [`docs/manuals/web_ui_design_system.md`](./web_ui_design_system.md)

The **Wabb-Interface** is the real-time web remote controller for the Vialactée chandelier, built with React 18, TypeScript, Vite, and Tailwind CSS. It communicates with the Python backend via `GET /api/topology` and a full-duplex WebSocket (`ws://<ip>:8080/ws`).

---

## 1. Starting the Web Interface

### A. Automatic Startup via `Main.py`
In [`config/app_config.json`](../../config/app_config.json):
```json
{
  "startServer": true,
  "startWebApp": true
}
```
- When `startServer: true`, `Connector.py` starts the HTTP + WebSocket server on `0.0.0.0:8080` (and serves `wabb-interface/dist/` if pre-built).
- When `startWebApp: true` (and `startServer: true`), `Main.py` automatically launches the Vite dev server on `0.0.0.0:5173`.
- *(Note: On Windows desktop runs, `Main.py` defaults `startServer` to `False` unless explicitly enabled to prevent port `:8080` collisions across rapid restarts).*

### B. Standalone Frontend Development (Vite Dev Server)
To edit React components with hot module reloading:
```bash
cd wabb-interface
npm install
npm run dev
```
Open `http://localhost:5173/`. (Requires the Python backend running on `:8080`).

---

## 2. Interface Pages & Controls (4-Tab Navigation)

| Tab | Component | Primary Functions |
| :--- | :--- | :--- |
| **1. Live Deck** | [`src/components/pages/LiveDeck.tsx`](../../wabb-interface/src/components/pages/LiveDeck.tsx) | Select curated mood palettes (`select_mood`), trigger immediate transitions (**GO** `go_to_next_configuration`), freeze/unfreeze automatic transitions (**HOLD / LIVE** `lock_current_configuration`), trigger a high-energy drop (**DROP** `manual_drop`), and tune master **Luminosity** (`set_luminosity`), **Sensibility** (`set_sensibility`), and **Auto Trans (s)** (`set_auto_transition_time`). |
| **2. Topology** | [`src/components/pages/TopologyEditor.tsx`](../../wabb-interface/src/components/pages/TopologyEditor.tsx) | Interactive 2D patchbay loaded dynamically from `GET /api/topology`. Inspect any physical strip (`v1`–`v4`, `h1`–`h4`, `c1`–`c3` in `full`; `s1`–`s3` in `small`), override its active mode (`select_segment_mode`), or flip its direction (`toggle_segment_direction`, `UP` $\leftrightarrow$ `DOWN`). |
| **3. Mode Settings** | [`src/components/pages/ModeSettings.tsx`](../../wabb-interface/src/components/pages/ModeSettings.tsx) | Auto-generates sliders, switches, and dropdowns from each mode's `get_settings_schema()` (`modeSettingsCatalog`). Sends `set_mode_setting` over WebSocket, updating live segment instances immediately and persisting overrides under `mode_settings` in `config/app_config.json`. |
| **4. System** | [`src/components/pages/SystemSetup.tsx`](../../wabb-interface/src/components/pages/SystemSetup.tsx) | Displays live backend connection status, active hardware profile (`FULL`: 2 Channels · 11 Segments, or `SMALL`: 1 Channel · 3 Segments), and host maintenance actions (`restart_python_loop`, `restart_raspberry_pi`) gated by backend capability flags. |

---

## 3. Connecting from Another Device (Phone / Laptop to Raspberry Pi)

### Step 1: Same Network
Connect both the Raspberry Pi and your phone/laptop to the **same Wi-Fi network** (or mobile hotspot).

### Step 2: Find the Raspberry Pi's IP Address
On the Raspberry Pi terminal, run:
```bash
hostname -I
```
Note the first IPv4 address (e.g. `192.168.1.42`).

### Step 3: Start Vialactée on the Raspberry Pi
```bash
~/vialactee/run-vialactee.sh
```
Wait until the console logs show both servers listening:
- WebSocket / API server on `http://0.0.0.0:8080`
- Vite Web UI server on `http://0.0.0.0:5173/`

### Step 4: Open the Browser on Your Phone or Laptop
Navigate to:
```text
http://<PI_IP>:5173
```
*(or `http://<PI_IP>:8080` if serving the production static build from `wabb-interface/dist/`)*. The frontend automatically connects its WebSocket to `ws://<PI_IP>:8080/ws`.

### Troubleshooting Connection Issues

| Symptom | Cause & Fix |
| :--- | :--- |
| **Page does not load at all** | Verify both devices are on the same subnet, `Main.py` is running with `"startServer": true` and `"startWebApp": true`, and you used `<PI_IP>` (not `localhost`). |
| **UI loads, but status shows `Disconnected`** | Port `8080` is blocked or the Python backend stopped. Check `ufw` on the Pi (`sudo ufw allow 5173/tcp && sudo ufw allow 8080/tcp`). |
| **Works on home Wi-Fi, fails on school/enterprise Wi-Fi** | Client/AP isolation is blocking peer-to-peer LAN traffic. Use a phone hotspot or dedicated router. |
| **Raspberry Pi IP changed after reboot** | Re-run `hostname -I` or assign a DHCP reservation on your router. |
