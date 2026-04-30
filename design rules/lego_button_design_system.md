# Tactile Lego Button Design System

This document serves as the official reference for creating perfectly spaced, 3D interactive Lego buttons in the Vialactée web interface. Following these rules ensures that all future buttons maintain perfect symmetry, physically accurate stud alignment, and dynamic text illumination.

## 1. The Core Principles

A "Lego Button" in this system is constructed via a layered architecture:
1. **The Baseplate (`button`)**: The physical colored block with smooth edges and 3D bevels.
2. **The Grid Boundary (`.drop-stud-grid`)**: An absolutely positioned container that controls exactly where studs are allowed to appear, preventing them from bleeding onto the smooth edges.
3. **The Matrix (React Array)**: A 2D array of `0`s (red background studs) and `1`s (illuminated white studs) that allows us to draw pixel-art text with Lego pieces.
4. **The Studs (`.stud`)**: The individual circles that shrink to fit the grid perfectly, utilizing radial gradients to simulate 3D cylindrical lighting.

---

## 2. React Structure & Matrix Logic

To create a button that "spells" a word using illuminated studs, use a 2D array mapped to a CSS Grid.

### The Matrix Pattern
Define a base pattern for the text. Use `1` for the illuminated text color, and `0` for the baseplate color.
```tsx
const textPattern = [
  // Example for "HI"
  [ 1, 0, 1,   0,   1, 1, 1 ],
  [ 1, 1, 1,   0,   0, 1, 0 ],
  [ 1, 0, 1,   0,   0, 1, 0 ],
  [ 1, 0, 1,   0,   1, 1, 1 ]
];
```

### The Ultra-Wide Padding
To ensure the button can stretch dynamically across large screens without running out of background studs, wrap the text matrix with an arbitrary number of blank columns (e.g., 20 `0`s on both sides).
```tsx
const paddedPattern = textPattern.map(row => [
  ...Array(20).fill(0), // 20 blank left columns
  ...row,               // Center text
  ...Array(20).fill(0)  // 20 blank right columns
]);
```

### The JSX Rendering
```tsx
<button className="giant-drop-button">
  <div className="drop-stud-grid">
    {paddedPattern.flat().map((isWhite, i) => (
      <div key={i} className={`stud ${isWhite ? 'stud-white' : 'stud-red'}`}></div>
    ))}
  </div>
</button>
```

---

## 3. CSS Architecture

### The Baseplate (Button)
The button relies heavily on multi-layered `box-shadow` properties to create physical depth (a bright top edge, a dark bottom edge, and a drop shadow).
```css
.giant-drop-button {
  position: relative;
  height: 160px; /* Fixed height for consistent rows */
  background-color: var(--lego-red);
  border-radius: 6px;
  border: 2px solid #1a1a1a;
  
  /* 3D Plastic Bevel Effect */
  box-shadow: 
    inset 0 4px 0 rgba(255,255,255,0.25), /* Top highlight */
    inset 0 -8px 0 rgba(0,0,0,0.3),       /* Bottom shadow */
    inset -6px 0 0 rgba(0,0,0,0.2),       /* Right shadow */
    0 10px 20px rgba(0,0,0,0.6);          /* Outer drop shadow */
}
```

### The Grid Boundary (The Secret to Smooth Margins)
To prevent studs from bleeding into the 3D bevels, the grid container **must** be `position: absolute` with inset margins and `overflow: hidden`.
* **Vertical padding (`top/bottom`)**: Match the bevel thickness (e.g., `18px`).
* **Horizontal padding (`left/right`)**: Increase this to create thicker smooth borders on the sides (e.g., `34px`).

```css
.drop-stud-grid {
  position: absolute;
  top: 18px; bottom: 18px; 
  left: 34px; right: 34px; /* Wider to create clean smooth borders */
  overflow: hidden; /* CRITICAL: Slices off extra background studs */
  
  display: grid;
  grid-template-rows: repeat(4, 1fr); /* 4 rows high */
  
  /* FORCE EXACT COLUMN WIDTH to guarantee perfect mathematical spacing */
  /* If rows are 30px tall, columns MUST be 30px wide */
  grid-template-columns: repeat(59, 30px); /* 20 + 19(text) + 20 */
  
  justify-content: center; /* Centers the massive 59-column grid */
  place-items: center; /* Centers the studs inside their 30x30 cells */
  pointer-events: none;
}
```

### The Individual Studs
The studs achieve their 3D look using two layered `radial-gradient` backgrounds. 
To control the **spacing (gap)** between studs, keep the CSS Grid cells fixed (e.g., `30x30px`), but change the `max-width` and `max-height` of the `.stud` element.
* **Cell = 30px**. **Stud = 23px**. 
* Result: A perfect `7px` uniform gap between all studs both vertically and horizontally.

```css
.stud {
  width: 100%;
  aspect-ratio: 1/1;
  border-radius: 50%;
  
  /* Size constraint. Reduce these to increase the gap! */
  max-width: 23px;
  max-height: 23px;
  
  /* Cylinder Lighting Simulation */
  background-image: 
    radial-gradient(circle at 35% 35%, rgba(255,255,255,0.4) 0%, transparent 30%),
    radial-gradient(circle at 50% 50%, transparent 50%, rgba(0,0,0,0.5) 70%, transparent 80%);
}

.stud-white {
  background-color: #fff;
  /* Extra glow for illuminated text studs */
  box-shadow: 0 0 15px rgba(255,255,255,0.9), inset 0 0 5px rgba(0,0,0,0.2);
}
```
