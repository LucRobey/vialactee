# Vialactée Signature Design System: "Tactile Dark Mode Lego"

> **NOTE:** In this project, the term "Design Signatures" refers to the core technical blueprints and UX specifications that guide the web application's development.

## 1. Core Philosophy

The signature design language of the Vialactée web application is a unique fusion of **modern, sleek dark mode UI** and **highly tactile, 3D-rendered Lego brick elements**. It bridges the gap between playful, physical hardware interaction and professional, high-tech software management.

## 2. Visual Aesthetic & Textures

* **The Baseplate:** The core interactive canvas must utilize a dark charcoal or slate grey Lego baseplate texture. It should feature a strict grid of realistic studs with subtle specular highlights.
* **Plastic Realism:** All interactive Lego elements (nodes, buttons, sliders) should have a glossy, ABS plastic finish. They require realistic edge highlights, and subtle surface imperfections to ground them in reality.
* **Skeuomorphic Integration:** The physical Lego elements should exist within a clean, matte dark-mode interface (sidebars, headers, standard panels) to provide contrast and ensure readability of dense data.

## 3. Color Palette

* **Backgrounds & Chrome:** Deep charcoal, slate greys, and near-blacks (e.g., `#121212` to `#2A2A2A`).
* **Lego Bricks (Primary):** Highly saturated, classic building block colors used for functional color-coding:
  * 🔴 **Cherry Red:** Critical actions (e.g., DROP button, Central Hubs).
  * 🔵 **Cobalt Blue:** Data centers, presets, secondary systems.
  * 🟢 **Forest Green:** API gateways, active healthy states, specific presets.
  * 🟡 **Bright Yellow / Orange:** Server racks, warnings, intermediate states.
* **Lighting & Accents:** Emissive "neon" glows for active states, data flow, and LED simulations (e.g., localized perimeter edge-glowing on baseplates, active mechanical structural clamps, and digital dot-matrix displays for BPM).

## 4. Typography

* **Font Family:** Clean, geometric, and technical sans-serif (e.g., Inter, Roboto, or DIN).
* **Styling:**
  * Bold, uppercase lettering for labels placed directly on bricks (simulating printed plastic).
  * Crisp, white or light-grey text for standard UI panels and navigation.
  * Dot-matrix or glowing digital fonts for numerical readouts (e.g., the 128 BPM counter).
  * **Physical Typography:** Large text (like the "DROP" button) is physically constructed using individual 1x1 pieces snapped onto the grid. This leverages a "messy builder" aesthetic: mixing square and round plates, randomly rotating them slightly, substituting smooth flat tiles (no top stud), and deliberately mismatching colors (e.g., grey and yellow amidst white).

## 5. UI Component Library

* **Buttons (e.g., "DROP"):** Thick, multi-stud bricks (e.g., 3x3 or 2x4). They should visually depress when clicked, pushing deeper into the z-axis.
* **Sliders & Faders:** Recessed, smooth dark tracks with brightly colored 1x1 or 1x2 brick sliders indicating levels.
* **Topology / Canvas Nodes:** Distinct color-coded blocks representing hardware components, servers, or stage elements.
* **Connections / Wires:** Smooth tile lines or glowing fiber-optic paths routed strictly at 90-degree angles between nodes on the stud grid.
* **Standard UI Panels:** Traditional data displays (CPU/RAM progress bars, network health stats, alert lists) should remain flat and sleek, sitting completely outside or hovering clearly above the tactile baseplate.

## 6. Grid & Layout Rules

* **Absolute Coordinate Snapping:** Everything on the tactile canvas *must* strictly adhere to the stud grid using Absolute Coordinates (e.g., `col=X, row=Y`), abandoning traditional CSS Flexbox or Grid-flow logic entirely. This prevents sub-pixel drifting or unwanted spacing.
* **The LEGO_MATH Engine:** All dimensions are derived from a centralized math variable (`1 Stud = 30px`). Physical interactive components must subtract a `4px` tolerance to render realistic physical plastic seams, while conceptual bounding boxes use true 30px multiples.
* **Spatial Hierarchy:** Larger, thicker blocks represent more critical systems or primary actions. Groupings should be explicitly mapped via coordinates to create clear, unmistakable zones on the baseplate.
