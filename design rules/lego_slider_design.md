# Tactile Lego Slider Design System

This document serves as the official reference for creating the vertical, grid-based "Lego Slider" components in the Vialactée web interface. This slider features a 3-column grid mimicking physical dark-slate Lego plates, a deeply recessed stud track, and an interactive 1x2 red brick as the slider thumb.

## 1. HTML / React Structure

The slider utilizes a CSS Grid wrapper to align three main columns: a left numerical scale, the central interactive groove, and a right numerical scale.

```tsx
<div className="lego-slider">
  <div className="slider-track-wrap">
    
    {/* Left Scale: Numbers 1 to 10 */}
    <div className="slider-scale">
      {[1,2,3,4,5,6,7,8,9,10].map(n => <span key={n}>{n}</span>)}
    </div>
    
    {/* Center Groove with Input */}
    <div className="slider-track-groove">
       <input type="range" className="vertical-slider" min="1" max="100" defaultValue="60" />
    </div>
    
    {/* Right Scale: Numbers 1 to 10 */}
    <div className="slider-scale">
      {[1,2,3,4,5,6,7,8,9,10].map(n => <span key={n}>{n}</span>)}
    </div>

  </div>
</div>
```

---

## 2. The Base Container & Grid

The slider body is fixed in dimensions to enforce a perfect `30x30px` grid square for every single number and stud.
* **Height**: 300px (10 blocks tall).
* **Width**: 90px (3 columns of 30px).

```css
.lego-slider {
  background-color: #1e2634; /* Base dark blue/slate */
  border: 2px solid #0f131a;
  border-radius: 4px;
  box-shadow: var(--plastic-shadow);
  padding: 0;
  position: relative;
  width: 90px;
  height: 300px; /* 10 rows of 30px */
  overflow: hidden;
}

.slider-track-wrap {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 30px 30px 30px;
  position: relative;
  z-index: 2;
}
```

---

## 3. The Number Scales (Grid Blocks)

The scales use `display: flex; flex-direction: column-reverse;` so that "1" sits at the bottom and "10" at the top. Each `span` mimics a single 1x1 Lego tile.

```css
.slider-scale {
  display: flex;
  flex-direction: column-reverse;
  height: 100%;
  padding: 0;
  margin: 0;
  pointer-events: none;
}

/* Individual 30x30px Block Tile */
.slider-scale span {
  width: 100%;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-weight: 800;
  font-size: 0.95rem;
  background-color: #2b374a;
  
  /* Top and Bottom Bevels to separate the blocks */
  border-top: 1px solid #41526b;
  border-bottom: 1px solid #1a2230;
  box-shadow: 
    inset 1px 0 2px rgba(255,255,255,0.05), 
    inset -1px 0 2px rgba(0,0,0,0.1);
  text-shadow: 0 1px 2px rgba(0,0,0,0.8);
}

/* Outer vertical grid lines */
.slider-scale:first-child span {
  border-right: 1px solid #141b26;
  border-left: 1px solid #141b26;
}
.slider-scale:last-child span {
  border-left: 1px solid #141b26;
  border-right: 1px solid #141b26;
}
```

---

## 4. The Recessed Track

The center track simulates a deep groove. We use intense inset shadows to create depth, and radial gradients to render subtle, dark vertical studs embedded inside the track.

```css
.slider-track-groove {
  width: 30px;
  height: 100%;
  background-color: #11161f;
  box-shadow: 
    inset 6px 0 8px rgba(0,0,0,0.7), 
    inset -6px 0 8px rgba(0,0,0,0.7);
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  
  /* Recessed Dark Studs */
  background-image: 
    radial-gradient(circle at 15px 15px, rgba(255,255,255,0.05) 0%, transparent 20%),
    radial-gradient(circle at 15px 15px, #18202d 0%, #18202d 30%, rgba(0,0,0,0.8) 35%, transparent 40%);
  background-size: 30px 30px; /* Aligns perfectly with the 30px grid cells */
  background-position: 0 0;
}
```

---

## 5. The 1x2 Red Brick (Slider Thumb)

To make a standard HTML input slide vertically, we apply `transform: rotate(-90deg)`.
Because of the rotation:
- HTML **Width** becomes vertical height on screen.
- HTML **Height** becomes horizontal width on screen.
- CSS Shadows shift (e.g., a left shadow becomes a bottom shadow).

```css
/* The Invisible Input */
.vertical-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 300px; /* Matches track HEIGHT */
  height: 30px; /* Matches track WIDTH */
  background: transparent;
  transform: rotate(-90deg); /* Flips it vertical */
  transform-origin: center;
  outline: none;
  z-index: 10;
  margin: 0;
  padding: 0;
  position: absolute;
}

/* The 1x2 Red Brick Thumb */
.vertical-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  height: 28px; /* Visual Width */
  width: 60px;  /* Visual Height (2 grid blocks tall) */
  border-radius: 2px;
  cursor: pointer;
  background-color: #d32020;
  
  /* Multi-gradient drawing */
  background-image: 
    /* 1. The horizontal divider (simulates 2 separate 1x1 blocks pushed together) */
    linear-gradient(90deg, transparent 48%, rgba(0,0,0,0.6) 49%, rgba(0,0,0,0.6) 51%, rgba(255,255,255,0.3) 52%, transparent 53%),
    /* 2. Top stud highlight */
    radial-gradient(circle at 25% 50%, rgba(255,255,255,0.2) 0%, transparent 15%),
    /* 3. Top stud shadow */
    radial-gradient(circle at 25% 50%, transparent 20%, rgba(0,0,0,0.4) 25%, transparent 35%),
    /* 4. Bottom stud highlight */
    radial-gradient(circle at 75% 50%, rgba(255,255,255,0.2) 0%, transparent 15%),
    /* 5. Bottom stud shadow */
    radial-gradient(circle at 75% 50%, transparent 20%, rgba(0,0,0,0.4) 25%, transparent 35%);
    
  /* 3D Bevel and Drop Shadow */
  box-shadow: 
    inset 0 3px 4px rgba(255,255,255,0.4),
    inset 0 -3px 4px rgba(0,0,0,0.5),
    inset 3px 0 4px rgba(255,255,255,0.3),
    inset -3px 0 4px rgba(0,0,0,0.3),
    -6px 0 10px rgba(0,0,0,0.8); /* Rotates to cast shadow downwards */
}

.vertical-slider::-webkit-slider-runnable-track {
  width: 100%;
  height: 100%;
  background: transparent;
  cursor: pointer;
}
```
