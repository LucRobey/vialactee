# Live Deck Design Rules & Logic

The **Live Deck** (`components/pages/LiveDeck.tsx`) is the primary performance interface for Vialactée. It is designed to be a high-contrast, tactile, and highly responsive dashboard for the light jockey. The visual language strictly adheres to the "Dark Mode Lego" aesthetic, ensuring that every interactive element feels like a physical piece snapped onto a baseplate.

## 1. Grid & Math Logic System

*   **The Infinite Baseplate:** The entire background is a deep grey (`#1a1e24`) baseplate. The studs are rendered using pure CSS radial gradients and are spaced precisely on a **30x30px grid**.
*   **The LEGO_MATH Engine:** Layouts are completely severed from standard web flex/grid models. Every component on the page is driven by a central Math Logic Panel where `1 Stud = 30px`, and physical pieces subtract a `4px` tolerance gap to simulate physical plastic seams.
*   **Modular "Rogue" Pieces:** To break up the monotony, the background is scattered with mismatched colored baseplates (Dark Blue, Dark Red, Olive Green, Yellow, etc.). These pieces take absolute X/Y stud coordinates and generate their physical bounds using the math engine.

## 2. Layout Architecture (Absolute Positioning)

The Live Deck is built on an absolute coordinate grid using the `<GridSpot>` wrapper. Components do not "flow"; they are pegged into exact coordinates (X, Y in studs).

### A. Left Column: Manual Overrides (three vertical sliders)
*   **Coordinate Plane:** `col=0`
*   **Purpose:** Direct tactile control over global visual / scheduling properties.
*   **Components:** Three vertical Lego sliders stacked inside a single dark "control rack" housing.
*   **Sliders:**
    *   **LUMINOSITÉ** (1 → 100, sends `set_luminosity`)
    *   **SENSIBILITÉ** (1 → 100, sends `set_sensibility`)
    *   **AUTO TRANS (S)** (5 → 300 seconds, sends `set_auto_transition_time`)
*   **Design:** Each slider is wrapped in an `.absurd-slider-mechanism` decorative cluster (Technic beams, guide rails, mounts, spinning gears, drop weights). Recessed tracks contain a thumb mimicking a 1x2 physical Lego brick. The label tile sits above each track on a white printed brick.

### B. Center Column: Telemetry & Transition Engine
*   **Coordinate Plane:** Starts at `col=4`
*   **Telemetry Bar:** Spans roughly 25 studs horizontally. Displays critical live stats sourced from `mode_master_state`/`state.system`:
    *   CPU TEMP (`system.cpuTempC`)
    *   PLAYLIST (`activePlaylist`)
    *   CONFIG (`activeConfiguration`)
    *   LATENCY (`system.dynamicAudioLatencyMs`)
*   **Central Mounting Baseplate:** Critical configuration and transition controls are mounted onto a large Orange baseplate (`col=7`). This baseplate features a localized LED circuit where only the outermost perimeter studs glow (Green for "Live" mode, Red for "Hold" mode), leaving the interior mounting studs a natural solid orange.
*   **Next Configuration / Transition Blocks:**
    *   Designed as **Flat Lego Tiles** (stud-less, glossy finish) hosting flat dropdowns.
    *   The Next Configuration row also exposes a round blue 2x2-style baton-pass button that fires `go_to_next_configuration` (queued configuration + selected transition).
*   **The DROP Button:** A massive red button mounted at `col=8, row=16` that emits a `manual_drop` instruction. Instead of glowing LEDs, the word "DROP" is physically constructed on its surface using individual 1x1 white Lego pieces (a mix of square and round plates). It features a "messy builder" aesthetic with slight random rotations, deliberate mismatched colored pieces (yellow and grey), and smooth "clear" tiles (tiles lacking a top stud).

### C. Right Column: Preset Blocks
*   **Coordinate Plane:** `col=35`
*   **Purpose:** Rapid firing of saved playlists.
*   **Design:** High-relief, bright colored bricks (Blue, Orange, Green, Purple, Yellow, Red, Cyan, Magenta) stacked absolutely at precise 3-stud vertical intervals (`row=2`, `row=5`, `row=8`, ...). The visible bricks are capped to the first eight playlists.
*   **Data Rule:** Preset bricks are generated only from `data/configurations.json` via `loadConfigurationStore()` and `state.playlists` from the `mode_master_state` WebSocket snapshot. Do not hardcode playlist names or add special synthetic entries such as `CUSTOM`.

## 3. Interaction Logic (The "Baton Pass")

The Live Deck supports a non-destructive "Queue and Drop" workflow that's crucial for live performance:
1.  **Select:** The user taps a preset brick on the right (sends `select_playlist`) or selects a queued saved configuration from the Next Configuration dropdown (sends `select_configuration`).
2.  **Transition:** The user picks a transition style from the Next Transition dropdown (`CUT`, `FADE IN/OUT`, `CROSSFADE`, sends `select_transition`).
3.  **Lock (optional):** Flipping the HOLD / LIVE switch toggles `lock_current_configuration` to freeze automatic progression and changes the orange baseplate glow color.
4.  **Baton Pass:** The round blue button next to the Next Transition dropdown fires `go_to_next_configuration` with the queued configuration and selected transition.
5.  **DROP:** The giant DROP button fires `manual_drop`, asking Mode_master to execute a music-drop style override.
6.  **Override:** At any time, the operator can ride the left-column sliders (luminosity, sensibility, auto-transition time) for instant master adjustments.

## 4. Runtime State Contract

The Live Deck hydrates from two sources:

* `GET /api/configurations` for saved playlist/configuration names (via `loadConfigurationStore()`).
* `mode_master_state` over `/ws` for the live active playlist, active configuration, queued configuration, selected transition, lock state, luminosity, sensibility, **auto-transition time**, and the telemetry subset (`system.cpuTempC`, `system.dynamicAudioLatencyMs`).

Luminosity, sensibility, and auto-transition time slider changes are persisted by Python into `config/app_config.json`, so closing or restarting the web app/backend restores the previous values.

The telemetry bar must show backend state, not local placeholder state. Dropdowns may start empty while the JSON file loads.

When the bridge is `connecting` or `closed`, the deck shows a `LIVE DATA STATUS` notice banner explaining that telemetry and playlist state may lag or that queued commands cannot be confirmed until the bridge reconnects.

## 5. Visual Priorities
*   **Legibility:** Labels on flat tiles must use dark text (`#1a1a1a`) for contrast against light grey. Labels on dark backgrounds must glow or use `var(--text-dim)`.
*   **Tactility:** Every button must have active state physics (`transform: translateY()`, adjusted shadows) to provide visual feedback that a physical piece was pressed.
*   **Strict Mathematical Alignment:** Standard web layouts (`justify-content`, `margin: auto`) are forbidden on the baseplate. Every element must be wrapped in a coordinate-based `<GridSpot>` to ensure rigid, pixel-perfect 30px snapping to the physical illusion.
