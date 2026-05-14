# Wabb Interface — Web App Functionality & Development Goals

This document describes what the **Wabb Interface** (React + Vite app in this folder) does today, how it connects to the Vialactée Python controller, and what the **intended end state** is for anyone maintaining the UI or onboarding agents.

For project-wide architecture, read the repository root [`project_overview.md`](../project_overview.md). For connector and state contracts, see [`README.md`](./README.md) and [`connectors/README.md`](../connectors/README.md). For topology UX rules, see [`design rules/topology.md`](./design%20rules/topology.md).

---

## 1. Purpose and role in Vialactée

The web app is the **official remote control** for the chandelier: it replaces a legacy native Android client so operators can use any device with a browser.

**End goal (product):** a single, polished control surface that lets a show operator (or installer):

- Drive **playlist rotation**, **configuration presets**, and **transitions** during a live event.
- Inspect and steer **per-segment** LED modes and wiring direction in real time, and **author** presets that persist to disk when appropriate.
- Tune **per-mode parameters** for the active configuration without editing Python or JSON by hand.
- Monitor **host health**, **audio path**, and **output chain** status, and perform **controlled restarts** when the backend allows it.

**End goal (engineering):** the UI stays a thin client: **no hardcoded playlist or configuration names**; lists come from `data/configurations.json` via HTTP, while authoritative **live state** comes from the Python **Mode_master** over a WebSocket snapshot stream.

---

## 2. Technical architecture (summary)

| Layer | Responsibility |
|--------|----------------|
| **HTTP** `GET/POST /api/configurations` | Load and persist the shared store: playlists + per-playlist configuration presets (`SegmentConfiguration`: segment modes, directions, optional `modeSettings`). |
| **WebSocket** `/ws` (default `ws://<host>:8080/ws`, override with `VITE_WABB_WS_URL`) | Bidirectional: UI sends **instructions** (JSON); server pushes **`mode_master_state`** snapshots. |
| **`src/utils/configurationStore.ts`** | Typed boundary for the configurations API; normalizes malformed entries defensively. |
| **`src/utils/controlBridge.ts`** | Singleton WebSocket client: subscribe to state, subscribe to connection status, queue outbound messages when offline, validate inbound `mode_master_state`. |
| **`src/utils/useBridgeStatus.ts`** | Maps socket lifecycle to UI (`open` / `connecting` / `closed`). |

**Dev vs production:** Vite’s `vite.config.ts` implements the same `/api/configurations` routes against `../data/configurations.json`. When the stack is run via `Main.py`, `connectors/Connector.py` serves the API and reloads playlists after saves.

---

## 3. Global shell (`App.tsx`)

- **Tab navigation:** Live Deck, Stage Architect (WIP), Topology, Mode Settings, System.
- **Branding:** Vialactée / Luminos header assets.
- **Connection pill:** LIVE / CONNECTING / OFFLINE from WebSocket status.
- **Notice when offline:** warns that live values may be stale and queued commands may not apply until reconnect.

---

## 4. Tab: Live Deck (`LiveDeck.tsx`)

**Role:** primary **show control** surface during performance.

### Data sources

- **Configurations:** initial list from `loadConfigurationStore()`; playlist list can be refreshed from WebSocket `state.playlists`.
- **Live state:** `subscribeModeMasterState` — luminosity, sensibility, transition lock, selected transition, active playlist/configuration, queued next configuration, playlists array, plus a subset of telemetry (CPU temp, dynamic audio latency).

### User actions (WebSocket `page: "live_deck"`)

| Action | Payload (concept) | Effect |
|--------|-------------------|--------|
| `set_luminosity` | `{ value: number }` | Global brightness control (1–100 in UI). |
| `set_sensibility` | `{ value: number }` | Global audio sensitivity control (1–100 in UI). |
| `select_configuration` | `{ configuration: string }` | Chooses which saved preset is queued / targeted as “next” (dropdown options come from JSON for the active playlist). |
| `select_transition` | `{ transition: string }` | One of `CUT`, `FADE IN/OUT`, `CROSSFADE`. |
| `go_to_next_configuration` | `{ configuration, transition }` | Applies transition to advance to the selected configuration. |
| `lock_current_configuration` | `{ locked: boolean }` | HOLD vs LIVE: locks or unlocks automatic progression. |
| `manual_drop` | (none) | Triggers a manual music-drop style event on the backend. |
| `select_playlist` | `{ playlist: string }` | Switches active playlist (preset brick buttons; max eight visible bricks, slice of available playlists). |

### UI highlights

- Lego-themed **vertical sliders** for luminosity and sensibility.
- **Telemetry strip:** CPU temp, current playlist name, active configuration name, measured dynamic audio latency.
- **Preset bricks:** one button per playlist (up to eight) with color cycling.

---

## 5. Tab: Topology (`TopologyEditor.tsx` and topology components)

**Role:** **spatial map** of chandelier segments plus **inspector** for segment mode/direction and **preset authoring** (playlists/configurations).

### Visual / interaction model

- Segment layout and styling follow [`design rules/topology.md`](./design%20rules/topology.md): stud grid (`LEGO_MATH`, `GridSpot`), SVG “cables,” junction boxes at intersections, tile typography, mode switchboard.
- **TopologyMap:** clickable segments; per-segment direction toggle.
- **TopologySegmentInspector:** mode list from backend `availableModes` (fallback from initial topology-derived list before first snapshot).
- **TopologyConfigurationPanel:** configuration name field, selector, rename/delete/save (save rules depend on editor mode).
- **TopologyPlaylistPanel:** playlist name draft, create/rename/delete playlist, cycle playlist with `select_playlist_slot`.
- **TopologyEditorModeSwitch:** `LIVE` | `MODIFY` | `BUILD`.

### Editor modes (contract)

| Mode | Segment display | Persistence |
|------|-----------------|-------------|
| **LIVE** | Mirrors `mode_master_state` (active playlist/configuration, each segment’s `mode` / `direction`). | Runtime only: segment changes are **instructions**, not `POST /api/configurations`. Re-loading a saved configuration restores file-backed modes. |
| **MODIFY** | Edits the selected saved configuration; switching from LIVE re-applies stored preset to segments. | `POST /api/configurations` on save/rename/delete playlist or configuration; then `modify_configuration` so Mode_master reloads from disk. |
| **BUILD** | Same as MODIFY for local segment edits; save can add or overwrite configurations in the playlist. | Same HTTP + `build_configuration` or `modify_configuration` after save. |

**LIVE pending edits:** because snapshots can arrive ~30 Hz and briefly show stale modes, the editor keeps a **short-lived pending map** per segment so UI does not flicker backward after a click until the server snapshot matches.

### Configuration file mapping

- Python expects segment keys like **`Segment v4`**, **`Segment h32`** (see `TopologyEditor` save path: `` `Segment ${seg.id}` ``).
- `SegmentConfiguration` in TS: `name`, `modes`, optional `way` (direction per segment key), optional `modeSettings` (cloned on save from live `activeModeSettings` when present).

### User actions (WebSocket `page: "topology"`)

| Action | Purpose |
|--------|---------|
| `select_segment` | Focus a segment in the inspector. |
| `select_segment_mode` | Set segment’s visual mode (live or local preview). |
| `toggle_segment_direction` | Flip `UP`/`DOWN` for a segment. |
| `set_editor_mode` | Notify backend of LIVE / MODIFY / BUILD. |
| `select_playlist_slot` | Cycle playlist with direction `next` / `previous`. |
| `select_configuration` | Load a configuration from the current playlist (updates local segment map from store). |
| `modify_configuration` | After disk save or rename: tell Mode_master to reload the named configuration in the playlist. |
| `build_configuration` | After BUILD save: notify backend of new/updated preset. |

---

## 6. Tab: Mode Settings (`ModeSettings.tsx`)

**Role:** edit **per-mode tuning** for the **active configuration** using a schema **pushed by Python** (`modeSettingsCatalog`), not hardcoded in React.

### Data flow

- Subscribes to `mode_master_state.modeSettingsCatalog` and `mode_master_state.modeSettings`.
- Renders only modes that expose at least one setting.
- Controls: **switch**, **slider**, **list** per descriptor (`controlBridge.ts` types).

### User actions (WebSocket `page: "mode_settings"`)

| Action | Payload | Effect |
|--------|---------|--------|
| `set_mode_setting` | `{ mode, key, value }` | Updates live tuning; backend applies to segments using that mode. |

**Pending edits:** same pattern as topology LIVE — pending values merge over snapshots until the server reports matching values, avoiding rollback flicker.

---

## 7. Tab: System (`SystemSetup.tsx`)

**Role:** **read-only telemetry** plus **dangerous actions** gated by backend capability flags.

### Display (from `state.system`)

Examples include: CPU temperature, RAM/disk usage, Python loop FPS and health, simulation vs Pi hardware resolution, ESP32 reachability, phone Bluetooth status, microphone enabled flag, audio stream state/health, last sample age, dynamic latency, uptime, hostname, platform, connected **web client count**, and **last system action** feedback.

### User actions (WebSocket `page: "system"`)

| Action | Preconditions | Effect |
|--------|----------------|--------|
| `restart_python_loop` | Bridge open; `system.actions.restartPython.available` | Confirms with user; soft-restarts the controller process. |
| `restart_raspberry_pi` | Bridge open; `system.actions.rebootRaspberry.available` | Confirms with user; reboots the Pi host. |

If the bridge is offline, actions are disabled and a banner explains why.

---

## 8. Tab: Stage Architect (`StageArchitect.tsx`) — **WIP / planned**

**Current state:** placeholder page with a warning banner; not wired to WebSocket or configuration APIs.

**Intended end goal:** an **interactive stage mapper** (SVG or similar) complementary to Topology — likely for higher-level stage layout, zone grouping, or future spatial cues. Until implemented, operators should use **Topology**, **Mode Settings**, and **System** for live control (as stated in-app).

---

## 9. Mode master snapshot (`ModeMasterState`) — what the UI expects

The TypeScript shape in `controlBridge.ts` is the contract the UI validates on every `mode_master_state` message. Agents changing the backend must keep this in sync or update both sides.

**Highlights:**

- Playlist/configuration: `activePlaylist`, `activeConfiguration`, `queuedConfiguration`, `playlists`, `enabledPlaylists`.
- Transitions: `selectedTransition`, `transitionLocked`, `transitionState`, `transitionProgress`.
- Global sliders: `luminosity`, `sensibility`.
- Catalogs: `availableModes`, `segments` (per-segment id, name, mode, direction, blocked, targetMode, inTransition).
- Mode tuning: `modeSettingsCatalog`, `modeSettings`.
- Nested `system`: telemetry and `actions` capabilities/feedback.

---

## 10. Instruction envelope (all pages)

Every outbound message is a `WabbInstruction`:

```json
{
  "page": "live_deck | topology | mode_settings | system",
  "action": "string_action_name",
  "payload": {},
  "timestamp": 1715430000000
}
```

The bridge adds `timestamp` at send time.

---

## 11. Rules for developers and agents

1. **Never hardcode playlist or configuration names** in React — use `GET /api/configurations` and websocket-driven `playlists` / active names.
2. **Topology LIVE** never writes `configurations.json`; only **MODIFY** / **BUILD** saves use `POST /api/configurations`.
3. After persisting JSON, the UI must send **`modify_configuration`** or **`build_configuration`** so `Mode_master` reloads (see `TopologyEditor` save flows).
4. **Per-mode tuning** belongs in configuration-scoped `modeSettings` and flows through Mode_master; the Mode Settings tab only edits via `set_mode_setting`.
5. For deeper backend behavior (transitions, orchestration), read **`core/precisions/mode_master.md`** and connector docs before changing instruction handlers.

---

## 12. Development checklist (keeping this file useful)

When you add or change UI behavior:

- [ ] Update this file if user-visible capability, a new `action`, or a schema field changed.
- [ ] Ensure `controlBridge.ts` types and runtime guards match the Python payload.
- [ ] If topology persistence rules change, update [`design rules/topology.md`](./design%20rules/topology.md) as well.

---

*Last aligned with repository context: Live Deck, Topology (LIVE/MODIFY/BUILD), Mode Settings, System, Stage Architect placeholder, `configurationStore.ts`, `controlBridge.ts`, and [`project_overview.md`](../project_overview.md) §2–§3.*
