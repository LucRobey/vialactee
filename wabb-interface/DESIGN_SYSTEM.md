# Vialactée Web Interface — Design System & Architecture Guide (Agent DNA)

> **Identity & Purpose:**
> `wabb-interface` is the tactile, real-time control deck and hardware topology orchestrator for the **Vialactée Interactive Kinetic Chandelier**.
> It serves two core functions:
> 1. **Live Deck**: High-frequency performance control (BPM, speed, dynamic visual parameters, palette swapping, mode switching).
> 2. **Topology & Profiles**: Spatial mapping and hardware addressing of physical modular branches across the ceiling grid.

---

## 1. Aesthetic Vibe & Visual DNA: "Tactile Dark Lego meets Heavy Machinery"

The aesthetic is inspired by physical engineering testbenches, modular analog synthesizers, and LEGO® construction systems:
- **Baseplates & Studs**: Dark matte textured panels with physical stud grids (`#12151c` base, `#1e2430` studs with inset shadows).
- **Physical Depth**: Chamfered borders, bevels, subtle drop shadows, and inset grooves (`box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 4px 12px rgba(0,0,0,0.5)`).
- **Hazard Stripes & Diagnostic Markings**: High-contrast diagonal hazard headers (`repeating-linear-gradient(...)`) on hardware monitors and safety toggles.
- **OLED & Nixie Glow**: Neon accents against deep graphite/black:
  - Cyan / Electric Blue: `#00f0ff` (Primary diagnostics, active states, clock sync)
  - Amber / Industrial Gold: `#ffaa00` (Warnings, standby, mechanical controls)
  - Laser Green / Phosphor: `#00ff66` (Audio beat pulses, verified connections)
  - Warning Red / Crimson: `#ff3344` (Master kill switch, disconnects, over-voltage)
- **Monospace Typography**: JetBrains Mono, Fira Code, or clean tabular monospace numbers for all values, coordinates, and telemetry readings.

---

## 2. The LEGO® Spatial & Math Engine

Physical chandelier hardware modules (branches, hubs, power taps) correspond to modular blocks on a physical baseplate.

### Spatial Grid Invariants
| Property | Value | Notes |
| :--- | :--- | :--- |
| **Stud Size (`STUD_SIZE`)** | `30px` | The fundamental unit of distance. |
| **Stud Pitch (`STUD_PITCH`)** | `30px` | 1 stud = 30px x 30px square. |
| **Physical Tolerance (`TOLERANCE`)** | `4px` | Margin between adjacent modular bricks to prevent visual overlap. |
| **Origin (`(0, 0)`)** | Top-left | `(x, y)` in studs mapped to `x * 30px`, `y * 30px`. |

### Golden Rules of Grid Layout:
1. **Never use arbitrary CSS pixel absolute positioning for board elements**:
   Always calculate using stud coordinates:
   ```typescript
   left: `${x * STUD_SIZE}px`,
   top: `${y * STUD_SIZE}px`,
   width: `${width * STUD_SIZE - TOLERANCE}px`,
   height: `${height * STUD_SIZE - TOLERANCE}px`
   ```
2. **Component Placement via `<GridSpot>` / `<FitBoard>`**:
   The canvas uses `<FitBoard>` to scale the full physical matrix onto any viewport with crisp SVG/CSS transforms while preserving aspect ratio.
3. **Sine-Rotated Accents & Technic Connectors**:
   Hardware hubs and rotational joints use angled brackets, subtle 45°/90° rotational transforms, and Technic-style circular pins with radial depth gradients.

---

## 3. The 4 Cardinal State Rules

Every agent modifying UI code or bridge communication **must** adhere to these four immutable architectural rules:

### Rule 1: Live Transient vs. Persisted Configuration Separation
- **LIVE State** (BPM tap, audio volume, temporary parameter sliders, current running mode) lives in runtime memory and broadcasts via WebSocket at up to 30Hz.
- **PERSISTED Configuration** (Physical branch lengths, strip channel assignments, custom presets, hardware mappings) lives in JSON files via REST (`/api/configurations`, `/api/topology`).
- *Never save transient performance tweaks into permanent hardware configuration files without explicit user "Save/Commit" action.*

### Rule 2: Single Source of Truth (`Mode_master`)
- Python (`Core.py` / `AudioAnalyzer.py` / `modes/`) is the single source of truth for the active running state.
- The web frontend receives state snapshots via `controlBridge`.
- The frontend **reflects** backend state and issues **commands**; it does not simulate lighting math or mode logic independently.

### Rule 3: Protected Dragging & Input Rate Limiting
- Incoming 30Hz WebSocket snapshots will ruthlessly overwrite React state if sliders are bound directly to `liveState`.
- **Any interactive slider MUST implement dragging isolation**:
  1. Set `isDraggingRef.current = true` on `pointerDown`.
  2. Maintain a local draft value during drag.
  3. Send throttled delta updates (50–80ms cadence) via `sendThrottledSlider(...)`.
  4. On `pointerUp`, dispatch final value and set a cooldown timer (~200ms) before allowing incoming snapshots to update the slider again.

### Rule 4: Dynamic Hardware Topology & Schema Safety
- Chandelier hardware configurations vary (e.g., 6 branches vs. 12 branches, varying LED densities).
- Never hardcode branch counts or channel indices.
- Always defensively parse incoming snapshots using `normalizeModeMasterState(...)` with fallback defaults to prevent null-dereference crashes on partial payloads.

---

## 4. Component Hierarchy & Directory Architecture

```
wabb-interface/src/
├── components/
│   ├── pages/
│   │   ├── LiveDeck.tsx              # Real-time performance deck (BPM, modes, parameters)
│   │   ├── TopologyEditor.tsx        # Physical branch & LED hardware layout editor
│   │   ├── HardwareHealth.tsx        # Power, framerate, temperature & status telemetry
│   │   └── PresetsPlaylists.tsx      # Saved sequence and preset management
│   ├── controls/                     # Tactile knobs, sliders, rocker switches, hazard buttons
│   ├── topology/                     # GridSpot, FitBoard, BranchTile, StudGrid
│   └── common/                       # CyberPanel, HazardHeader, StatusBadge, Tooltip
├── utils/
│   ├── controlBridge.ts              # WebSocket link, heartbeat, snapshot normalizer
│   ├── configurationStore.ts         # REST API wrapper for topology & presets
│   └── audioVisualizerHelpers.ts     # FFT rendering, waveform buffers
├── App.tsx                           # Main chassis, tab router (persistent mounting)
├── main.tsx                          # React 19 root
└── index.css                         # Global CSS variables, stud patterns, fonts
```

---

## 5. UI Recipes & Styling Conventions

### Hazard Header Pattern
```tsx
<div className="bg-[repeating-linear-gradient(-45deg,#ffaa00,#ffaa00_10px,#1a1a1a_10px,#1a1a1a_20px)] h-2 w-full rounded-t" />
```

### Stud Matrix Background
```css
.stud-grid {
  background-color: #12151c;
  background-image: radial-gradient(circle, #252b3b 2px, transparent 2.5px);
  background-size: 30px 30px;
  background-position: 15px 15px;
}
```

### Machined Bevel Panel
```tsx
<div className="bg-[#181c24] border border-[#2a3242] shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_8px_24px_rgba(0,0,0,0.6)] rounded-lg p-4">
  {children}
</div>
```

---

## 6. Development & Quality Mandates
- **TypeScript**: Strict mode enabled. No `as any` escape hatches.
- **React 19**: Adhere strictly to React 19 rules (no ref mutations during render, clean `useEffect` dependencies).
- **ESLint**: Must pass `npm run lint` with 0 warnings and 0 errors before any commit.
- **Build**: Must succeed with `npm run build` without missing assets or broken imports.
