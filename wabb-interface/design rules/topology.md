# Topology Editor Design Rules

The **Topology Editor** (`TopologyEditor.tsx`) is the interactive visual mapper for the Vialactée hardware. It serves as both a physical representation of the LED chandelier segments and an interactive configuration console (The Dynamic Inspector). 

Operating under the overarching **"Vialactée by Luminos"** branding, the editor combines a sleek, cosmic identity with heavy, tactile hardware controls. This document outlines the specific design rules, layout math, and styling techniques used to achieve its physical, "Heavy Machinery" / Lego-inspired aesthetic.

## 1. The Grid System (`GridSpot` & `LEGO_MATH`)
The entire page operates on an absolute coordinate system based on Lego studs.
* **1 Stud = 30px**.
* `GridSpot`: A wrapper component that positions children via `col` and `row` props (e.g., `left: col * 30, top: row * 30`).
* All sizes and gaps are calculated using the `LEGO_MATH` engine (e.g., `LEGO_MATH.physicalSize(studs) = (studs * 30) - 4px`) to account for the physical 4px tolerance gap between real bricks.

## 2. The Interactive SVG Mapper
The main area of the page is a top-down view of the chandelier's LED segments.
* **Segments**: Rendered as physical `rogue-piece` elements that glow in their respective colors. They feature a `var(--highlight)` and `var(--shadow)` stud overlay so they look like translucent plates.
* **Selection**: Clicking a segment applies a strong white border and outer glow, marking it as active for the Inspector.
* **Junction Boxes**: The component runs an AABB (Axis-Aligned Bounding Box) collision check across all segments. Where horizontal and vertical segments intersect, it automatically spawns a physical dark-grey "Junction Box" brick over the intersection.

## 3. Physical Wiring (SVG Layer)
To bridge the gap between the theoretical map and the physical "Inspector" console, heavy-duty cables connect the segments to the panel.
* Implemented using absolute `<svg>` paths laid over the grid.
* Uses Bezier curves (`C`) to create natural drooping loops.
* Features multi-layered styling: a thick dark stroke, a translucent white stroke offset by `-2px` for a glossy highlight, and an SVG drop-shadow filter to separate it from the baseplate.
* The ends of the cables have multi-layered `<circle>` elements simulating thick rubber plugs plugging into the segments and the console.

## 4. The Dynamic Inspector (Console)
Located in the bottom-left space, the Inspector is where users change the mode of the currently selected segment. It is designed to look like a separate piece of heavy diagnostic hardware snapped onto the board.
* **The Baseplate**: A heavy red (`#d22020ff`) panel textured with radial gradients to simulate Technic pin holes.
* **Technic Pins**: The four corners feature detailed SVG/CSS-drawn cross-axle pins locking the console into the map.
* **The Screen Bezel**: An inset, deep dark grey area defined by thick, color-shifted borders (`borderTopColor` lighter, `borderBottomColor` darker) and heavy inset shadows to look carved out of the plastic.
* **Hazard Stickers**: Titles like "SYSTEM MODES" use `repeating-linear-gradient` to create construction-style yellow/black hazard stripes.

## 5. Hand-Placed Typography (1x1 Tiles)
Instead of rendering digital text for the selected segment name and current mode, the interface "spells" them out using physical 1x1 Lego tiles.
* Each letter is a separate physical tile (`1 var(--stud)` wide/tall).
* **Pseudo-Random Rotation**: To prevent it from looking perfectly digital, each tile receives a slight rotation (`transform: rotate(angle)`), calculated using a deterministic sine function (`Math.sin(index * seed) * 3.5`). This mimics the slight imperfections of a human hand placing square tiles onto a studded board.

## 6. Mode Selection Buttons
The available modes are listed as a physical switchboard.
* Each mode is a dark tile that "pops" to a bright yellow (`#fcd000`) when selected.
* Beside each tile is a physical LED indicator. When active, it glows with the selected segment's color. When inactive, it has dark inner shadows to look like an unpowered diode.

## 7. Playlist And Configuration Data

Topology uses `data/configurations.json` as its persistence layer:

* It loads playlists/configurations through `src/utils/configurationStore.ts` and `GET /api/configurations`.
* It saves **only from `MODIFY` or `BUILD`** through `POST /api/configurations`. The red **SAVE** control in `LIVE` is blocked: live tweaks must not write the JSON file (use `MODIFY` or `BUILD` to persist a preset).
* The saved JSON shape is `{ "playlists": string[], "configurations": Record<string, Configuration[]> }`.
* Segment mode keys must stay in Python format (`Segment v4`, `Segment h32`, etc.) so `Mode_master` can apply them directly.
* The UI must not seed fake playlist names. If the JSON file is empty, the controls should display an empty/no-playlist state.
* Playlist management lives in the same inspector panel: `NEW` creates a saved playlist with the typed name, and `REN` renames the selected playlist while preserving all configurations attached to it.
* Configuration management in `MODIFY` mode has a selector plus editable name field: `REN` renames the selected configuration and `DEL` removes it from the current playlist.

## 8. Editor Modes: LIVE, MODIFY, and BUILD

### `LIVE` (performance mirror)

* Segment tiles and the inspector follow `mode_master_state` from `/ws` (`activePlaylist`, `activeConfiguration`, per-segment `mode` / `direction`).
* Changing a segment **mode** or **direction** sends `select_segment_mode` / `toggle_segment_direction` on `/ws`. That updates the running `Segment` in Python only; it does **not** change rows in `data/configurations.json`. Re-applying the same saved configuration (from the deck or after reload) restores the modes stored in the file.
* Snapshots arrive at ~30 Hz. A snapshot can briefly show the previous mode **before** the server applies the instruction. The UI keeps a short-lived **pending edit** per segment so local state does not flicker back until the snapshot matches the choice (case-insensitive mode name match).
* Switching **LIVE → MODIFY** re-applies the currently selected playlist/configuration from the in-memory store (`apiConfigurations`) onto the segment list so the **UPDATE** action edits the saved preset, not a stale live override left in React state.

### `MODIFY` and `BUILD` (authoring)

* Local segment mode/direction edits stay in React until the user saves via `POST /api/configurations`, then `modify_configuration` / `build_configuration` instructions notify `Mode_master` to reload from disk.
