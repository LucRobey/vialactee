# Lego UI Developer Blueprint: Building a New Page

This document serves as the technical blueprint for constructing new pages in the Vialactée web app. It codifies the React components, CSS variables, and layout math required to maintain the "Tactile Dark Mode Lego" aesthetic.

## 1. The LEGO_MATH Engine & Grid System

All layouts completely bypass standard CSS Flexbox/Grid in favor of an **Absolute Coordinate Grid**. 

### Core CSS Variables
Define these in your root CSS to ensure all components scale and fit physically:
```css
:root {
  --stud: 30px;        /* The absolute physical size of 1x1 unit */
  --tolerance: 4px;    /* The physical gap between adjacent plastic pieces */
}
```

### Component Dimensions
When sizing a physical piece (like a button or a tile), ALWAYS subtract the tolerance from the total stud width/height so that pieces placed next to each other have realistic seams:
```css
.lego-piece {
  width: calc(10 * var(--stud) - var(--tolerance));
  height: calc(3 * var(--stud) - var(--tolerance));
}
```

### The `<GridSpot>` Wrapper
Every element MUST be placed on the baseplate using a coordinate wrapper. The origin `(0,0)` is the top-left of the canvas.
```tsx
const GridSpot = ({ col, row, children, style = {} }) => (
  <div style={{
    position: 'absolute',
    left: `calc(${col} * var(--stud))`,
    top: `calc(${row} * var(--stud))`,
    ...style
  }}>
    {children}
  </div>
);
```
**Usage:**
```tsx
<GridSpot col={8} row={16}>
   <MyButton />
</GridSpot>
```

---

## 2. The Canvas & Rogue Background Pieces

### The Master Baseplate
The root container of any page must simulate a massive dark-grey Lego baseplate:
```css
.baseplate-canvas {
  background-color: #1a1e24; /* Base plastic color */
  background-image:
    /* Stud highlight */
    radial-gradient(circle at 12px 12px, rgba(255, 255, 255, 0.08) 0%, transparent 3px),
    /* Stud body */
    radial-gradient(circle at 15px 15px, #1a1e24 0%, #1a1e24 6px, #11141a 7px, transparent 8px),
    /* Stud shadow */
    radial-gradient(circle at 16px 17px, rgba(0, 0, 0, 0.4) 0%, transparent 9px);
  background-size: var(--stud) var(--stud);
}
```

### Random "Rogue" Pieces
To break up the visual monotony, scatter random flat baseplates across the grid. Use a deterministic generation array (so they don't jump around on re-renders):
```tsx
const roguePieces = [
  { col: 2, row: 5, w: 4, h: 4, color: '#00205b' }, // Dark Blue
  { col: 18, row: 12, w: 6, h: 2, color: '#6b3fa0' }, // Purple
];

{roguePieces.map((p, i) => (
  <GridSpot key={i} col={p.col} row={p.row} style={{ zIndex: -1 }}>
    <div style={{
       width: `calc(${p.w} * var(--stud))`, 
       height: `calc(${p.h} * var(--stud))`,
       backgroundColor: p.color,
       borderRadius: '4px',
       boxShadow: 'inset 2px 2px 4px rgba(255,255,255,0.1), inset -2px -2px 4px rgba(0,0,0,0.4)',
       /* Re-apply stud gradients here if the rogue piece has studs! */
    }}></div>
  </GridSpot>
))}
```

---

## 3. Physical Typography ("Messy Builder" aesthetic)

For large textual elements (like giant DROP buttons), do not use web fonts. Construct the word using a binary grid matrix (0s and 1s) representing 1x1 pieces.

### The Mapping Logic
```tsx
{characterMatrix.flat().map((isSolid, i) => {
  if (!isSolid) return <div key={i} className="stud stud-red"></div>; // Base surface
  
  // Randomize rotation (-7 to +7 degrees) for tactile realism
  const rotation = ((i * 17) % 15) - 7;
  // Mix square and round plates
  const isSquare = (i * 13) % 2 === 0;

  // Deliberately inject mismatched colors / "clear" smooth tiles
  const isYellow = i === 8 || i === 24;
  const isClear = [4, 11].includes(i);

  let colorClass = isYellow ? 'piece-yellow' : '';
  let clearClass = isClear ? 'piece-clear' : '';

  return (
    <div 
      key={i} 
      className={`stud-piece ${isSquare ? 'piece-square' : 'piece-circle'} ${colorClass} ${clearClass}`}
      style={{ transform: `rotate(${rotation}deg)` }}
    ></div>
  );
})}
```
**CSS Rules for Pieces:**
* `.stud-piece`: `width: 26px`, `box-shadow` for elevation, `position: relative`.
* `.stud-piece::after`: The 16px circular stud on top.
* `.piece-clear::after`: `display: none` (creates a smooth 1x1 flat tile without a fixing circle).

---

## 4. Advanced Lighting: Perimeter Edge-Glow

When a component (like a mounting baseplate) needs to glow to indicate state (e.g., Green for Live, Red for Hold), only the **perimeter studs** should light up, while the inner area remains solid plastic.

**Technique: The Z-Index Mask**
1. **The Glowing Base (`::before`)**: Cover the entire baseplate with the illuminated colored studs (using `background-image` radial gradients).
2. **The Mask (`::after`)**: Inset the element by exactly 1 stud (`top: var(--stud); bottom: var(--stud);` etc.). Give it the solid plastic background color and normal, non-glowing studs.

```css
/* 1. Base Plate */
.large-orange-baseplate {
  position: relative;
  background-color: #ff8200;
  z-index: 1;
}

/* 2. The Glowing Layer (Red State) */
.large-orange-baseplate.glow-red::before {
  content: "";
  position: absolute;
  inset: 0;
  /* Glowing Red Studs */
  background-image: radial-gradient(circle at 15px 15px, #f56565 0%, #e53e3e 7px, transparent 9px);
  background-size: var(--stud) var(--stud);
}

/* 3. The Solid Plastic Mask */
.large-orange-baseplate::after {
  content: "";
  position: absolute;
  inset: var(--stud); /* Shrink by exactly 1 stud on all sides */
  background-color: #e67300;
  /* Normal Orange Studs */
  background-image: radial-gradient(circle at 15px 15px, #e67300 0%, #b35900 8px, transparent 9px);
  background-size: var(--stud) var(--stud);
}
```
This forces the bright glowing studs to only peak out along the absolute edge of the baseplate.

---

## 5. Global Branding ("Vialactée by Luminos")

To reinforce the dual identity of the application (the cosmic "Vialactée" project powered by the "Luminos" hardware interface), brand logos are integrated directly into the global navigation (`tab-bar` in `App.tsx`).

### Logo Integration Rules
*   **Format:** Use transparent `.png` files for logos (`vialactee.png`, `luminos.png`) to ensure they blend seamlessly with the dark plastic baseplate backgrounds.
*   **Styling for Depth:** Instead of standard `box-shadow`, use CSS `filter: drop-shadow(...)` on the logos. This applies the shadow to the exact opaque contours of the logo, making the graphics feel like they are painted or physically raised above the UI.
*   **Connecting Typography:** Bridging text (like "by") should use a tech-focused monospace font (`VT323`) to contrast with the sleek logos and ground the branding in the "diagnostic hardware" aesthetic.

```css
.brand-vialactee {
  height: 40px;
  object-fit: contain;
  filter: drop-shadow(0 0 5px rgba(255, 255, 255, 0.2)); /* Cosmic glow */
}

.brand-luminos {
  height: 28px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.8)); /* Physical hardware drop-shadow */
}
```
