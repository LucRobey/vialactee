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
| **`src/utils/configurationStore.ts`** | Typed boundary for the configurations API; normalizes malformed entries defensively. Exposes `loadConfigurationStore()` (HTTP) and `loadConfigurationFileStore()` (bundled raw JSON for the Configurator). |
| **`src/utils/controlBridge.ts`** | Singleton WebSocket client: subscribe to state, subscribe to connection status, queue outbound messages when offline, validate inbound `mode_master_state`. |
| **`src/utils/useBridgeStatus.ts`** | Maps socket lifecycle to UI (`open` / `connecting` / `closed`). |

**Dev vs production:** Vite's `vite.config.ts` implements the same `/api/configurations` routes against `../data/configurations.json`. When the stack is run via `Main.py`, `connectors/Connector.py` serves the API and reloads playlists after saves.

---

## 3. Global shell (`App.tsx`)

- **Tab navigation:** Live Deck, Topology, Configurator, Mode Settings, System (five tabs).
- **Branding:** Vialactée / Luminos header assets.
- **Connection pill:** LIVE / CONNECTING / OFFLINE from WebSocket status.
- **Notice when offline:** warns that live values may be stale and queued commands may not apply until reconnect.

---

## 4. Tab: Live Deck (`LiveDeck.tsx`)

**Role:** primary **show control** surface during performance.

### Data sources

- **Configurations:** initial list from `loadConfigurationStore()`; playlist list can be refreshed from WebSocket `state.playlists`.
- **Live state:** `subscribeModeMasterState` — luminosity, sensibility, **auto-transition time** (`autoTransitionTime`, in seconds), transition lock, selected transition, active playlist/configuration, queued next configuration, playlists array, plus a subset of telemetry (CPU temp, dynamic audio latency).

### User actions (WebSocket `page: "live_deck"`)

| Action | Payload (concept) | Effect |
|--------|-------------------|--------|
| `set_luminosity` | `{ value: number }` | Global brightness control (1–100 in UI). |
| `set_sensibility` | `{ value: number }` | Global audio sensitivity control (1–100 in UI). |
| `set_auto_transition_time` | `{ value: number }` | Auto-rotation cadence in seconds (5–300 in UI). |
| `select_configuration` | `{ configuration: string }` | Chooses which saved preset is queued / targeted as "next" (dropdown options come from JSON for the active playlist). |
| `select_transition` | `{ transition: string }` | One of `CUT`, `FADE IN/OUT`, `CROSSFADE`. |
| `go_to_next_configuration` | `{ configuration, transition }` | Applies transition to advance to the selected configuration (round blue baton-pass button). |
| `lock_current_configuration` | `{ locked: boolean }` | HOLD vs LIVE: locks or unlocks automatic progression and toggles the orange baseplate's perimeter glow. |
| `manual_drop` | (none) | Triggers a manual music-drop style event on the backend (giant DROP button). |
| `select_playlist` | `{ playlist: string }` | Switches active playlist (preset brick buttons; up to eight visible bricks). |

### UI highlights

- Three Lego-themed **vertical sliders** stacked in the left column: Luminosité, Sensibilité, Auto Trans (S).
- **Telemetry strip:** CPU temp, current playlist name, active configuration name, measured dynamic audio latency.
- **Preset bricks:** one button per playlist (up to eight), color-cycled through Blue, Orange, Green, Purple, Yellow, Red, Cyan, and Magenta.
- **Notice banners:** the deck surfaces `LIVE DATA STATUS` and `CONFIGURATION STORE` banners whenever the WebSocket bridge is not `open` or the configuration file fails to load.

---

## 5. Tab: Topology (`TopologyEditor.tsx` and topology components)

**Role:** **LIVE spatial map** of chandelier segments plus a read/touch **inspector** for live segment mode/direction. Preset authoring lives in the dedicated **Configurator** tab (see §5b).

The `TopologyEditor` component is shared between this tab and the Configurator and accepts an `allowedModes` prop (default `['LIVE', 'MODIFY', 'BUILD']`). The Topology tab passes `['LIVE']`, which:

- Hides the `TopologyEditorModeSwitch` (only one mode available).
- Hides the `TopologyConfigurationPanel` and `TopologyPlaylistPanel` (those belong to Configurator).
- Keeps the topology map + segment inspector wired to live `mode_master_state` snapshots.

### Visual / interaction model

- Segment layout and styling follow [`design rules/topology.md`](./design%20rules/topology.md): stud grid (`LEGO_MATH`, `GridSpot`), SVG "cables," junction boxes at intersections, tile typography, mode switchboard.
- **TopologyMap:** clickable segments; per-segment direction toggle.
- **TopologySegmentInspector:** mode list from backend `availableModes` (fallback from initial topology-derived list before first snapshot).

**LIVE pending edits:** because snapshots can arrive ~30 Hz and briefly show stale modes, the editor keeps a **short-lived pending map** per segment so the UI does not flicker backward after a click until the server snapshot matches.

---

## 5b. Tab: Configurator (`Configurator.tsx` → `TopologyEditor` with `allowedModes={['MODIFY', 'BUILD']}`)

**Role:** **preset authoring** surface for playlists and configurations. Uses the same topology canvas as the Topology tab, but exposes:

- **TopologyEditorModeSwitch:** toggles between `MODIFY` and `BUILD` (no `LIVE` here).
- **TopologyConfigurationPanel:** configuration name field, selector, rename/delete/save (save rules depend on editor mode).
- **TopologyPlaylistPanel:** playlist name draft, create/rename/delete playlist, cycle playlist with `select_playlist_slot`.

Because the Configurator never enters LIVE, `mode_master_state` snapshots do not overwrite the local segment map (the underlying `TopologyEditor` only mirrors snapshots when `editorMode === 'LIVE'`). Selecting a configuration in the dropdown re-applies stored modes/directions to the canvas. The Configurator also bypasses HTTP for the initial load by using `loadConfigurationFileStore` (Vite raw import of `data/configurations.json`), so live snapshots cannot race the authoring view.

### Editor modes (contract)

| Mode | Segment display | Persistence |
|------|-----------------|-------------|
| **MODIFY** | Edits the selected saved configuration; selecting a config in the dropdown re-applies its stored preset to segments. | `POST /api/configurations` on save/rename/delete playlist or configuration; then `modify_configuration` so Mode_master reloads from disk. |
| **BUILD** | Same as MODIFY for local segment edits; save can add a new configuration or, with confirm-overwrite, replace an existing one in the playlist. | Same HTTP + `build_configuration` after save. |

### Configuration file mapping

- Python expects segment keys like **`Segment v4`**, **`Segment h32`** (see `TopologyEditor` save path: `` `Segment ${seg.id}` ``).
- `SegmentConfiguration` in TS: `name`, `modes`, optional `way` (direction per segment key), optional `modeSettings` (cloned on save from live `activeModeSettings` when present, falling back to the existing preset's `modeSettings`).

### User actions (WebSocket `page: "topology"`)

| Action | Purpose |
|--------|---------|
| `select_segment` | Focus a segment in the inspector. |
| `select_segment_mode` | Set the segment's visual mode (live or local preview). |
| `toggle_segment_direction` | Flip `UP` / `DOWN` for a segment. |
| `set_editor_mode` | Notify backend of LIVE / MODIFY / BUILD. |
| `select_playlist_slot` | Cycle playlist with direction `next` / `previous`. |
| `select_configuration` | Load a configuration from the current playlist (updates local segment map from store). |
| `modify_configuration` | After disk save or rename: tell Mode_master to reload the named configuration in the playlist. |
| `build_configuration` | After BUILD save: notify backend of a new/updated preset. |

> Both the Topology and Configurator tabs send instructions on the `topology` page; the backend distinguishes intent via the `set_editor_mode` action and the persistence-related actions.

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

## 8. Mode master snapshot (`ModeMasterState`) — what the UI expects

The TypeScript shape in `controlBridge.ts` is the contract the UI validates on every `mode_master_state` message. Agents changing the backend must keep this in sync or update both sides.

**Highlights:**

- Playlist/configuration: `activePlaylist`, `activeConfiguration`, `queuedConfiguration`, `playlists`, `enabledPlaylists`.
- Transitions: `selectedTransition`, `transitionLocked`, `transitionState`, `transitionProgress`.
- Global sliders: `luminosity`, `sensibility`, `autoTransitionTime`.
- Catalogs: `availableModes`, `segments` (per-segment id, name, mode, direction, blocked, targetMode, inTransition).
- Mode tuning: `modeSettingsCatalog`, `modeSettings`.
- Nested `system`: telemetry and `actions` capabilities/feedback.

---

## 9. Instruction envelope (all pages)

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

## 10. Rules for developers and agents

1. **Never hardcode playlist or configuration names** in React — use `GET /api/configurations` and websocket-driven `playlists` / active names.
2. **Topology (LIVE)** never writes `configurations.json`; only **Configurator** (MODIFY / BUILD) saves use `POST /api/configurations`.
3. After persisting JSON, the UI must send **`modify_configuration`** or **`build_configuration`** so `Mode_master` reloads (see `TopologyEditor` save flows used by the Configurator).
4. **Per-mode tuning** belongs in configuration-scoped `modeSettings` and flows through Mode_master; the Mode Settings tab only edits via `set_mode_setting`.
5. For deeper backend behavior (transitions, orchestration), read **`core/precisions/mode_master.md`** and connector docs before changing instruction handlers.

---

## 11. Development checklist (keeping this file useful)

When you add or change UI behavior:

- [ ] Update this file if user-visible capability, a new `action`, or a schema field changed.
- [ ] Ensure `controlBridge.ts` types and runtime guards match the Python payload.
- [ ] If topology persistence rules change, update [`design rules/topology.md`](./design%20rules/topology.md) as well.

---

*Last aligned with repository context: Live Deck (3 sliders + auto-transition), Topology (LIVE), Configurator (MODIFY/BUILD), Mode Settings, System, `configurationStore.ts`, `controlBridge.ts`, and [`project_overview.md`](../project_overview.md) §2–§3.*
