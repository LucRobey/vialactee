const fs = require('fs');
let css = fs.readFileSync('src/index.css', 'utf8');

const startMarker = '.pulsing-dot {';
const endMarker = '/* LCD SCREEN FX                             */';

let startIdx = css.indexOf(startMarker);
let endIdx = css.indexOf(endMarker);

if (startIdx !== -1 && endIdx !== -1) {
  const newContent = `.pulsing-dot {
  width: 8px;
  height: 8px;
  background: var(--lego-cyan);
  border-radius: 50%;
  animation: pulse-dot 1s infinite alternate;
}

@keyframes pulse-dot {
  0% { opacity: 0.3; box-shadow: 0 0 0 transparent; }
  100% { opacity: 1; box-shadow: 0 0 10px var(--lego-cyan); }
}

/* Equalizer Bars */
@keyframes equalizer {
  0% { height: 10%; }
  100% { height: 90%; }
}

/* ========================================= */
/* LEGO GRILLE SCROLLBAR                     */
/* ========================================= */
.custom-scrollbar::-webkit-scrollbar {
  width: 14px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background-color: #111;
  border-left: 2px solid rgba(0,0,0,0.8);
  border-right: 2px solid rgba(0,0,0,0.8);
  box-shadow: inset 2px 0 5px rgba(0,0,0,1);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #da291c;
  border-radius: 2px;
  border-top: 2px solid rgba(255,255,255,0.5);
  border-left: 1px solid rgba(255,255,255,0.3);
  border-bottom: 2px solid rgba(0,0,0,0.8);
  border-right: 1px solid rgba(0,0,0,0.6);
  background-image: 
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 3px,
      rgba(0,0,0,0.5) 3px,
      rgba(0,0,0,0.5) 5px,
      rgba(255,255,255,0.2) 5px,
      rgba(255,255,255,0.2) 6px
    );
  box-shadow: 2px 2px 5px rgba(0,0,0,0.8);
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #f03030;
}

/* ========================================= */
/* CHEESE SLOPE BUTTONS                      */
/* ========================================= */
.cheese-slope-btn {
  width: 30px;
  height: 30px;
  background-color: #fcd000;
  border: none;
  border-radius: 2px;
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #111;
  font-weight: 900;
  font-size: 0.8rem;
  box-shadow: 
    0 5px 8px rgba(0,0,0,0.7),
    inset 0 -2px 0 rgba(0,0,0,0.5);
  transition: all 0.1s;
  overflow: hidden;
}
.cheese-slope-btn.left {
  background-image: linear-gradient(90deg, rgba(0,0,0,0.2) 0%, rgba(255,255,255,0.7) 70%, rgba(255,255,255,0.9) 82%, #e0b800 86%, #ccaa00 100%);
  border-left: 1px solid rgba(0,0,0,0.4);
  border-right: 2px solid rgba(0,0,0,0.8);
  border-top: 2px solid rgba(255,255,255,0.4);
  border-bottom: 2px solid rgba(0,0,0,0.5);
}
.cheese-slope-btn.left::before {
  content: "";
  position: absolute;
  top: 0; bottom: 0; right: 4px; width: 1px;
  background: rgba(0,0,0,0.2);
}
.cheese-slope-btn.right {
  background-image: linear-gradient(-90deg, rgba(0,0,0,0.2) 0%, rgba(255,255,255,0.7) 70%, rgba(255,255,255,0.9) 82%, #e0b800 86%, #ccaa00 100%);
  border-right: 1px solid rgba(0,0,0,0.4);
  border-left: 2px solid rgba(0,0,0,0.8);
  border-top: 2px solid rgba(255,255,255,0.4);
  border-bottom: 2px solid rgba(0,0,0,0.5);
}
.cheese-slope-btn.right::before {
  content: "";
  position: absolute;
  top: 0; bottom: 0; left: 4px; width: 1px;
  background: rgba(0,0,0,0.2);
}
.cheese-slope-btn:active {
  transform: translateY(2px);
  box-shadow: 
    0 1px 2px rgba(0,0,0,0.6),
    inset 0 -1px 0 rgba(0,0,0,0.8);
}

/* ========================================= */
`;
  // need to prepend the /* LCD SCREEN FX to what was sliced off
  const endSlice = css.slice(endIdx);
  const finalCss = css.slice(0, startIdx) + newContent + endSlice;
  fs.writeFileSync('src/index.css', finalCss, 'utf8');
  console.log('Fixed CSS');
} else {
  console.log('Markers not found');
}
