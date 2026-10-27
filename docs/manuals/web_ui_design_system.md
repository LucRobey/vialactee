# Wabb-Interface UI Design System & Lego Blueprint

> **Location:** `docs/manuals/web_ui_design_system.md` (Tier 2 Operational Manual)  
> **Source Directory:** [`wabb-interface/src/`](../../wabb-interface/src/)  
> **Operator Manual:** [`docs/manuals/web_interface_manual.md`](./web_interface_manual.md)  
> **Wire Protocol:** [`docs/architecture/api_and_wire_protocol.md`](../architecture/api_and_wire_protocol.md)

The **Wabb-Interface** uses a tactile, physical **Lego Baseplate & Brick** design language engineered for zero-scroll single-screen operation on mobile and desktop viewports.

---

## 1. Visual Identity & Tactile Signatures

1. **Physical ABS Plastic Materiality:**
   - Every panel, button, fader, and badge is rendered as a physical Lego plate or tile snapped onto a recessed dark baseplate.
   - Plates use multi-layered directional lighting (`inset 0 2px 3px rgba(255,255,255,0.4)` top bevel, `inset 0 -3px 4px rgba(0,0,0,0.45)` bottom edge, and `0 6px 0` physical brick thickness with `translateY(4px)` press physics).
2. **Perimeter Edge-Glow (Under-Lighting):**
   - Active mood bricks and selected segments cast a colored LED glow (`box-shadow`) onto the dark baseplate studs around their perimeter, while the plastic brick body itself remains opaque.
3. **1x1 Physical Typography (`dropLetterTiles.ts`):**
   - Primary headers and the **DROP** trigger are built from individual `1x1` Lego tiles embossed with bold characters and given subtle organic rotation jitter (`-3deg` to `3deg`) so they read as hand-snapped plastic pieces.
4. **Rogue Pieces:**
   - Major structural plates can shift `1` stud (`30px`) off-grid via `LEGO_MATH.position(studIndex)` to break rigid digital symmetry while preserving exact stud alignment.
5. **Subtle Toy Branding:**
   - Stud crowns and plate corners carry micro-embossed `WABB` and set number `42182` markings at low opacity.

---

## 2. `LEGO_MATH` & The Spatial Grid Engine

All layout geometry is governed by [`wabb-interface/src/utils/legoMath.ts`](../../wabb-interface/src/utils/legoMath.ts):

```ts
export const LEGO_MATH = {
  STUD: 30,
  TOLERANCE: 4,
  grid: (studs: number) => studs * 30,
  physicalSize: (studs: number) => (studs * 30) - 4,
  position: (studIndex: number) => (studIndex * 30) + 2,
};
```

- **Plate Sizing (`LEGO_MATH.physicalSize(studs)`):**
  - Every Lego plate of size `w x h` studs has exact pixel dimensions:
    $$\text{width} = w \times 30 - 4\text{ px}, \quad \text{height} = h \times 30 - 4\text{ px}$$
  - Combined with a `2px` offset on each side (`LEGO_MATH.position(studIndex)`), adjacent plates sit `4px` apart (`TOLERANCE: 4`), exposing the underlying baseplate seam.
- **`<FitBoard>` ([`src/components/layout/FitBoard.tsx`](../../wabb-interface/src/components/layout/FitBoard.tsx)):**
  - Measures the available viewport via `ResizeObserver` and applies a uniform CSS `scale()` transform so the entire `cols x rows` Lego baseplate fits inside the screen with zero scrollbars.
- **`<GridSpot>` ([`src/components/layout/GridSpot.tsx`](../../wabb-interface/src/components/layout/GridSpot.tsx)):**
  - Positions children at explicit 1-indexed stud coordinates (`col`, `row`, `w`, `h`) on the `<FitBoard>` using `LEGO_MATH.position()` and `LEGO_MATH.physicalSize()`.

---

## 3. State & Data Synchronization Rules

1. **Optimistic Locking with Command Acknowledgment:**
   - When an operator clicks a brick or drags a slider, the UI updates optimistically and sends `{ page, action, payload, timestamp }` via [`src/utils/controlBridge.ts`](../../wabb-interface/src/utils/controlBridge.ts), reconciling state when the backend replies with `{"ok": true, "received": "<action>", "result": {...}}` and subsequent `{"type": "mode_master_state", "payload": {...}}` broadcasts.
2. **Dynamic Topology Single Source of Truth (AXIOM-03):**
   - Never hardcode segment names, counts, or coordinates in React components. [`src/utils/topologyStore.ts`](../../wabb-interface/src/utils/topologyStore.ts) fetches `GET /api/topology` (backed by `config/segments_full.json` or `config/segments_small.json`) and adapts automatically to both `full` (11 segments: `v1`–`v4`, `h00`, `h10`, `h11`, `h20`, `h30`, `h31`, `h32`) and `small` (3 segments: `s1`–`s3`) profiles.
3. **Schema-Driven Mode Settings:**
   - [`src/components/pages/ModeSettings.tsx`](../../wabb-interface/src/components/pages/ModeSettings.tsx) renders controls dynamically from `modeSettingsCatalog` (`Mode.get_settings_schema()`), never from hardcoded per-mode forms.

---

## 4. Frontend Directory Structure (`wabb-interface/src/`)

```text
wabb-interface/src/
├── App.tsx                                       # Top-level shell, header nav, WebSocket status
├── main.tsx                                      # React 18 root mount
├── index.css                                     # Global Tailwind & physical ABS plastic styles
├── components/
│   ├── common/
│   │   └── NoticeBanner.tsx                      # Connection & status notification bar
│   ├── layout/
│   │   ├── FitBoard.tsx                          # Auto-scaling Lego baseplate container
│   │   └── GridSpot.tsx                          # 1-indexed stud coordinate placement wrapper
│   ├── pages/
│   │   ├── LiveDeck.tsx                          # Tab 1: Mood bricks, GO/HOLD/DROP, master faders
│   │   ├── TopologyEditor.tsx                    # Tab 2: 2D chandelier patchbay & segment override
│   │   ├── ModeSettings.tsx                      # Tab 3: Schema-driven per-mode parameter tuning
│   │   └── SystemSetup.tsx                       # Tab 4: Hardware profile telemetry & host reboot
│   └── topology/
│       ├── TopologyMap.tsx                       # Interactive SVG/stud strip & Bezier cable canvas
│       ├── TopologyInspectorShell.tsx            # Inspector frame for the selected segment
│       └── TopologySegmentInspector.tsx          # Per-segment mode selector & UP/DOWN direction switch
├── constants/
│   ├── dropLetterTiles.ts                        # 1x1 physical letter tile definitions for DROP button
│   └── topologyData.ts                           # Fallback topology & UI layout constants
└── utils/
    ├── controlBridge.ts                          # WebSocket client, optimistic state & command dispatch
    ├── legoMath.ts                               # 30px stud grid math & stud background generator
    ├── topologyStore.ts                          # /api/topology fetcher & layout normalizer
    └── useBridgeStatus.ts                        # React hook subscribing to controlBridge state
```
