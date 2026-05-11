# Live Deck Design Rules & Logic

The **Live Deck** is the primary performance interface for Vialactée. It is designed to be a high-contrast, tactile, and highly responsive dashboard for the light jockey. The visual language strictly adheres to the "Dark Mode Lego" aesthetic, ensuring that every interactive element feels like a physical piece snapped onto a baseplate.

## 1. Grid & Math Logic System

*   **The Infinite Baseplate:** The entire background is a deep grey (`#1a1e24`) baseplate. The studs are rendered using pure CSS radial gradients and are spaced precisely on a **30x30px grid**.
*   **The LEGO_MATH Engine:** Layouts are completely severed from standard web flex/grid models. Every component on the page is driven by a central Math Logic Panel where `1 Stud = 30px`, and physical pieces subtract a `4px` tolerance gap to simulate physical plastic seams.
*   **Modular "Rogue" Pieces:** To break up the monotony, the background is scattered with mismatched colored baseplates (Dark Blue, Dark Red, Olive Green, Yellow, etc.). These pieces take absolute X/Y stud coordinates and generate their physical bounds using the math engine.

## 2. Layout Architecture (Absolute Positioning)

The Live Deck is built on a 40-stud-wide absolute coordinate grid using the `<GridSpot>` wrapper. Components do not "flow"; they are pegged into exact coordinates (X, Y in studs).

### A. Left Column: Manual Overrides (Sliders)
*   **Coordinate Plane:** `col=0` to `col=3`
*   **Purpose:** Direct tactile control over global visual properties.
*   **Components:** Vertical Lego Sliders.
*   **Design:** Sliders span a physical width of 3 studs and height of 10 studs, bounded mathematically to avoid grid drift. Recessed tracks contain a thumb mimicking a 1x2 physical Lego brick.

### B. Center Column: Telemetry & Transition Engine
*   **Coordinate Plane:** Starts at `col=4`
*   **Telemetry Bar:** Spans 25 studs horizontally. Displays critical live stats (CPU usage, active Playlist, current Configuration, Latency).
*   **Central Mounting Baseplate:** Critical configuration and transition controls are mounted onto a large Orange baseplate (`col=7`). This baseplate features a localized LED circuit where only the outermost perimeter studs glow (Green for "Live" mode, Red for "Hold" mode), leaving the interior mounting studs a natural solid orange.
*   **Next Configuration / Transition Blocks:** 
    *   Designed as **Flat Lego Tiles** (stud-less, glossy finish).
    *   Coordinate locked directly beneath telemetry on the orange baseplate, allowing users to queue visual states.
*   **The DROP Button:** A massive red button executing the queued configuration. Located at `col=8, row=16`. Instead of glowing LEDs, the word "DROP" is physically constructed on its surface using individual 1x1 white Lego pieces (a mix of square and round plates). It features a "messy builder" aesthetic with slight random rotations, deliberate mismatched colored pieces (yellow and grey), and smooth "clear" tiles (tiles lacking a top stud).

### C. Right Column: Preset Blocks
*   **Coordinate Plane:** `col=30` to `col=38`
*   **Purpose:** Rapid firing of saved playlists.
*   **Design:** High-relief, bright colored bricks (Blue, Orange, Green, Purple, etc.) stacked absolutely at precise 3-stud vertical intervals (`row=1`, `row=4`, `row=7`, etc.).
*   **Data Rule:** Preset bricks are generated only from `data/configurations.json` via `loadConfigurationStore()` and `state.playlists` from the `mode_master_state` WebSocket snapshot. Do not hardcode playlist names or add special synthetic entries such as `CUSTOM`.

## 3. Interaction Logic (The "Baton Pass")

The Live Deck is built around a non-destructive "Queue and Drop" workflow, crucial for live performance:
1.  **Select:** The user taps a preset brick on the right (or manually selects one from the Next Configuration dropdown).
2.  **Transition:** The user selects a transition style (Cut, Fade, Sweep).
3.  **Lock:** (Optional) The user flips the "LOCK TRANS" switch if they want to freeze the current settings and prevent accidental overwrites.
4.  **Execute:** The user hits the giant "DROP" button. Only at this exact moment are the queued settings dispatched to the Python backend to update the DMX/visual hardware.
5.  **Override:** At any time, regardless of the drop state, the user can ride the left-column sliders for instant master overrides (brightness, strobe speed, etc.).

## 4. Runtime State Contract

The Live Deck hydrates from two sources:

* `GET /api/configurations` for saved playlist/configuration names.
* `mode_master_state` over `/ws` for the live active playlist, active configuration, queued configuration, selected transition, lock state, luminosity, and sensibility.

The telemetry bar must show backend state, not local placeholder state. Dropdowns may start empty while the JSON file loads.

## 5. Visual Priorities
*   **Legibility:** Labels on flat tiles must use dark text (`#1a1a1a`) for contrast against light grey. Labels on dark backgrounds must glow or use `var(--text-dim)`.
*   **Tactility:** Every button must have active state physics (`transform: translateY()`, adjusted shadows) to provide visual feedback that a physical piece was pressed.
*   **Strict Mathematical Alignment:** Standard web layouts (`justify-content`, `margin: auto`) are forbidden on the baseplate. Every element must be wrapped in a coordinate-based `<GridSpot>` to ensure rigid, pixel-perfect 30px snapping to the physical illusion.
