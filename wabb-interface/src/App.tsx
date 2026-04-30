import { useState } from 'react'
import './index.css'

// ============================================================================
// 🧱 LEGO MATH ENGINE: Central Logic Panel for Grid & Physical Placement
// All sizes, gaps, and coordinates in the app derive from these core equations.
// ============================================================================
export const LEGO_MATH = {
  STUD: 30,         // 1 Stud = exactly 30px
  TOLERANCE: 4,     // The microscopic 4px physical gap between touching pieces

  // 1. Math for Conceptual Containers (Grid layout width/height)
  grid: (studs: number) => studs * 30,

  // 2. Math for Physical Rendered Pieces (Total footprint minus tolerance gap)
  physicalSize: (studs: number) => (studs * 30) - 4,

  // 3. Math for Absolute Map Positioning (Centers the piece within its conceptual trench)
  position: (studIndex: number) => (studIndex * 30) + 2,
};
// ============================================================================

// Page Components (Stubs for now)
const dropStudPattern = [
  [1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0],
  [1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1],
  [1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0],
  [1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0]
];
const wideDropStudPattern = dropStudPattern.map(row => [
  ...Array(20).fill(0),
  ...row,
  ...Array(20).fill(0)
]);

const GridSpot = ({ col, row, children }: { col: number, row: number, children: React.ReactNode }) => (
  <div style={{ position: 'absolute', left: `${col * 30}px`, top: `${row * 30}px` }}>
    {children}
  </div>
);

const LiveDeck = () => {
  const [lumValue, setLumValue] = useState(60);
  const [sensValue, setSensValue] = useState(70);
  const [isHold, setIsHold] = useState(false);

  return (
    <div className="live-deck-grid">

      {/* ======================= LEFT COLUMN ======================= */}
      <GridSpot col={3} row={0}>
        <div className="lego-label">Luminosité</div>
      </GridSpot>
      <GridSpot col={3} row={1}>
        <div className="slider-container-group" style={{ position: 'relative', '--slider-val': lumValue } as React.CSSProperties}>
          <div className="absurd-slider-mechanism">
            <div className="absurd-chassis"></div>
            <div className="technic-beam beam-1"></div>
            <div className="technic-beam beam-2"></div>
            <div className="guide-rail rail-1"></div>
            <div className="guide-rail rail-3"></div>
            <div className="rail-mount mount-1"></div>
            <div className="rail-mount mount-2"></div>
            <div className="rail-mount mount-3"></div>
            <div className="absurd-weight weight-drop-1"></div>
            <div className="absurd-gear gear-spin-1"></div>
            <div className="absurd-gear gear-spin-2"></div>
          </div>
          <div className="lego-slider">
            <div className="slider-track-wrap">
              <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
              <div className="slider-track-groove">
                <input type="range" className="vertical-slider" min="1" max="100" value={lumValue} onChange={e => setLumValue(Number(e.target.value))} />
              </div>
              <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
            </div>
          </div>
        </div>
      </GridSpot>

      <GridSpot col={3} row={12}>
        <div className="lego-label">Sensibilité</div>
      </GridSpot>
      <GridSpot col={3} row={13}>
        <div className="slider-container-group" style={{ position: 'relative', '--slider-val': sensValue } as React.CSSProperties}>
          <div className="absurd-slider-mechanism">
            <div className="absurd-chassis"></div>
            <div className="technic-beam beam-1"></div>
            <div className="technic-beam beam-2"></div>
            <div className="guide-rail rail-1"></div>
            <div className="guide-rail rail-3"></div>
            <div className="rail-mount mount-1"></div>
            <div className="rail-mount mount-2"></div>
            <div className="rail-mount mount-3"></div>
            <div className="absurd-weight weight-drop-green"></div>
            <div className="absurd-gear gear-spin-1"></div>
            <div className="absurd-gear gear-spin-2"></div>
          </div>
          <div className="lego-slider">
            <div className="slider-track-wrap">
              <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
              <div className="slider-track-groove">
                <input type="range" className="vertical-slider" min="1" max="100" value={sensValue} onChange={e => setSensValue(Number(e.target.value))} />
              </div>
              <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
            </div>
          </div>
        </div>
      </GridSpot>


      {/* ======================= CENTER COLUMN ======================= */}
      {/* Telemetry Bar (3 studs tall, 25 wide) */}
      <GridSpot col={8} row={0}>
        <div className="stage-status-bar" style={{ width: '750px' }}>
          <div className="status-item">
            <span className="status-label" style={{ fontSize: '0.7rem' }}>CPU</span>
            <span className="status-value digital-font" style={{ fontSize: '1.4rem', color: 'var(--lego-orange)', textShadow: '0 0 5px var(--lego-orange)' }}>42%</span>
          </div>
          <div className="status-item" style={{ textAlign: 'center' }}>
            <span className="status-label" style={{ fontSize: '0.7rem' }}>PLAYLIST</span>
            <span className="status-value" style={{ fontSize: '1.1rem', color: 'var(--lego-cyan)', fontWeight: 800, letterSpacing: '1px' }}>TECHNO SET</span>
          </div>
          <div className="status-item" style={{ textAlign: 'center' }}>
            <span className="status-label" style={{ fontSize: '0.7rem' }}>CONFIG</span>
            <span className="status-value" style={{ fontSize: '1.1rem', color: 'var(--lego-purple)', fontWeight: 800, letterSpacing: '1px' }}>PEAK DROP</span>
          </div>
          <div className="status-item" style={{ textAlign: 'right' }}>
            <span className="status-label" style={{ fontSize: '0.7rem' }}>LATENCY</span>
            <span className="status-value digital-font" style={{ fontSize: '1.4rem', color: 'var(--lego-green)', textShadow: '0 0 5px var(--lego-green)' }}>12ms</span>
          </div>
        </div>
      </GridSpot>

      {/* Large Orange Baseplate Mount */}
      <GridSpot col={7} row={4} style={{ zIndex: 0 }}>
        <div className={`large-orange-baseplate ${isHold ? 'glow-red' : 'glow-green'}`} style={{ width: '810px', height: '330px' }}></div>
      </GridSpot>

      {/* Config Block */}
      <GridSpot col={8} row={5}>
        <div className="flat-lego-tile" style={{ width: '570px', height: '116px' }}>
          <div className="tile-label">NEXT CONFIGURATION :</div>
          <select className="lego-select" style={{ background: '#222', color: 'white', border: '2px solid #444', padding: '1rem 1.5rem', borderRadius: '6px', fontSize: '1.2rem', outline: 'none', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 'bold', width: '220px' }}>
            <option>TECHNO 1</option>
            <option>HOUSE 2</option>
            <option>LOFI</option>
            <option>DNB</option>
          </select>
        </div>
      </GridSpot>

      {/* Transition Block */}
      <GridSpot col={8} row={10}>
        <div className="flat-lego-tile" style={{ width: '570px', height: '116px' }}>
          <div className="tile-label">NEXT TRANSITION :</div>
          <div style={{ display: 'flex', gap: '30px', alignItems: 'stretch' }}>
            <select className="lego-select" style={{ background: '#222', color: 'white', border: '2px solid #444', padding: '1rem 1.5rem', borderRadius: '6px', fontSize: '1.2rem', outline: 'none', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 'bold', width: '150px' }}>
              <option>CUT</option>
              <option>FADE IN / OUT</option>
              <option>CROSSFADE</option>
            </select>
            <button className="lego-round-button bg-blue" style={{ margin: 0 }}>
              <div className="round-stud-grid">
                <div className="stud stud-blue"></div>
                <div className="stud stud-blue"></div>
                <div className="stud stud-blue"></div>
                <div className="stud stud-blue"></div>
              </div>
            </button>
          </div>
        </div>
      </GridSpot>

      {/* Lock Trans Switch */}
      <GridSpot col={28} row={5}>
        <label className="lock-switch-container">
          <input type="checkbox" className="heavy-duty-checkbox" checked={isHold} onChange={(e) => setIsHold(e.target.checked)} />

          <div className="lock-status-display">
            <span className="lock-text lock-text-hold">HOLD</span>
            <span className="lock-text lock-text-live">LIVE</span>
          </div>

          <div className="heavy-duty-track">

            <div className="mech-system">
              <div className="mech-gear gear-left"></div>
              <div className="mech-gear gear-right"></div>
              <div className="mech-weight weight-left"></div>
              <div className="mech-weight weight-right"></div>
              <div className="mech-piston"></div>
              <div className="mech-bolt bolt-left"></div>
              <div className="mech-bolt bolt-right"></div>
            </div>

            <div className="heavy-duty-brick">
              <div className="round-stud-grid-2x2">
                <div className="stud stud-red"></div>
                <div className="stud stud-red"></div>
                <div className="stud stud-red"></div>
                <div className="stud stud-red"></div>
              </div>
            </div>
          </div>
        </label>
      </GridSpot>

      {/* Drop Button */}
      <GridSpot col={8} row={16}>
        <div className="drop-button-container" style={{ width: '750px' }}>
          <button className="giant-drop-button" style={{ width: '100%' }}>
            <div className="drop-stud-grid">
              {(() => {
                let whiteIndex = 0;
                return wideDropStudPattern.flat().map((isWhite, i) => {
                  if (!isWhite) return <div key={i} className="stud stud-red"></div>;
                  
                  const currentIndex = whiteIndex++;
                  // Generate a pseudo-random rotation and shape
                  const rotation = ((i * 17) % 15) - 7;
                  const isSquare = (i * 13) % 2 === 0;

                  // Assign colors to specific indices (2 yellow, 1 grey, 5 clears)
                  const isYellow = currentIndex === 8 || currentIndex === 24;
                  const isGrey = currentIndex === 16;
                  const isClear = [4, 11, 18, 27, 34].includes(currentIndex);

                  let colorClass = '';
                  if (isYellow) colorClass = 'piece-yellow';
                  else if (isGrey) colorClass = 'piece-grey';

                  return (
                    <div 
                      key={i} 
                      className={`stud-piece ${isSquare ? 'piece-square' : 'piece-circle'} ${colorClass} ${isClear ? 'piece-clear' : ''}`}
                      style={{ transform: `rotate(${rotation}deg)` }}
                    ></div>
                  );
                });
              })()}
            </div>
          </button>
        </div>
      </GridSpot>


      {/* ======================= RIGHT COLUMN ======================= */}
      <GridSpot col={35} row={0}>
        <div className="lego-label" style={{ width: '240px' }}>Presets</div>
      </GridSpot>

      <GridSpot col={35} row={1}><button className="preset-brick bg-blue" style={{ width: '240px' }}>TECHNO 1 <span className="preset-num">1</span></button></GridSpot>
      <GridSpot col={35} row={4}><button className="preset-brick bg-orange" style={{ width: '240px' }}>HOUSE 2 <span className="preset-num">2</span></button></GridSpot>
      <GridSpot col={35} row={7}><button className="preset-brick bg-green" style={{ width: '240px' }}>LOFI <span className="preset-num">3</span></button></GridSpot>
      <GridSpot col={35} row={10}><button className="preset-brick bg-purple" style={{ width: '240px' }}>DNB <span className="preset-num">4</span></button></GridSpot>
      <GridSpot col={35} row={13}><button className="preset-brick bg-yellow" style={{ width: '240px' }}>DISCO <span className="preset-num">5</span></button></GridSpot>
      <GridSpot col={35} row={16}><button className="preset-brick bg-red" style={{ width: '240px' }}>BASS <span className="preset-num">6</span></button></GridSpot>
      <GridSpot col={35} row={19}><button className="preset-brick bg-cyan" style={{ width: '240px' }}>TRAP <span className="preset-num">7</span></button></GridSpot>
      <GridSpot col={35} row={22}><button className="preset-brick bg-magenta" style={{ width: '240px' }}>AMBIENT <span className="preset-num">8</span></button></GridSpot>
      <GridSpot col={35} row={25}><button className="preset-brick bg-dark-blue" style={{ width: '240px' }}>CUSTOM <span className="preset-num">9</span></button></GridSpot>

    </div>
  );
};

const StageArchitect = () => (
  <div className="panel">
    <h2>🗺️ The Stage Architect</h2>
    <p>Interactive stage mapper. Select segments to edit.</p>
    <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
      <div style={{ flex: 2, background: '#111', border: '1px solid #444', borderRadius: '8px', minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-dim)' }}>[ Interactive SVG Mapper ]</p>
      </div>
      <div style={{ flex: 1, background: '#1e1e1e', padding: '1rem', borderRadius: '8px' }}>
        <h3>Dynamic Inspector</h3>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Select a segment to edit...</p>
      </div>
    </div>
  </div>
)

const TopologyEditor = () => (
  <div className="panel">
    <h2>📐 Topology Layout Editor</h2>
    <p>Defining the physical layout of the environment.</p>
    <div style={{ marginTop: '2rem', background: '#111', border: '1px solid #444', borderRadius: '8px', minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: 'var(--text-dim)' }}>[ Interactive Grid Setup ]</p>
    </div>
  </div>
)

const AutoDJTuning = () => (
  <div className="panel">
    <h2>🎛️ Auto-DJ Tuning</h2>
    <p>Designing the rules of the autonomous light jockey.</p>

    <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
      <div className="panel" style={{ background: '#222' }}>
        <h3>Mode Configuration Frame</h3>
        <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '1rem' }}>Deep parameters mapped to global variables.</p>

        {/* Example Mode Card */}
        <div style={{ border: '1px solid #444', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
          <h4>🌈 Rainbow Mode</h4>
          <div className="lego-slider-container" style={{ marginTop: '1rem' }}>
            <label style={{ fontSize: '0.8rem' }}>Color Density</label>
            <div className="lego-slider-track">
              <input type="range" min="0" max="100" defaultValue="50" />
            </div>
          </div>
        </div>

        <div style={{ border: '1px solid #444', padding: '1rem', borderRadius: '8px' }}>
          <h4>☄️ Pulsar Mode</h4>
          <div className="lego-slider-container" style={{ marginTop: '1rem' }}>
            <label style={{ fontSize: '0.8rem' }}>Tail Length</label>
            <div className="lego-slider-track">
              <input type="range" min="0" max="100" defaultValue="70" />
            </div>
          </div>
        </div>
      </div>

      <div className="panel" style={{ background: '#222' }}>
        <h3>Global Automation</h3>
        <div className="lego-slider-container" style={{ marginTop: '1rem', marginBottom: '1.5rem' }}>
          <label>Trigger Interval</label>
          <div className="lego-slider-track">
            <input type="range" min="0" max="100" defaultValue="30" />
          </div>
        </div>
        <div className="lego-slider-container">
          <label>Sweep Duration</label>
          <div className="lego-slider-track">
            <input type="range" min="0" max="100" defaultValue="45" />
          </div>
        </div>
      </div>
    </div>
  </div>
)

const SystemSetup = () => (
  <div className="panel">
    <h2>⚙️ System & Setup</h2>
    <p>Hardware health monitoring and ultimate control. Danger zone.</p>
    <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
      <div style={{ flex: 1, background: '#111', padding: '1rem', borderRadius: '8px', border: '1px solid #444' }}>
        <h3 style={{ color: 'var(--text-dim)' }}>Telemetry</h3>
        <h1 className="digital-font" style={{ fontSize: '3rem', margin: '1rem 0' }}>65°C</h1>
        <p>CPU Temp</p>
        <h1 className="digital-font" style={{ fontSize: '3rem', margin: '1rem 0', color: 'var(--lego-green)', textShadow: '0 0 10px var(--lego-green)' }}>60 FPS</h1>
        <p>Python Loop</p>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <button className="lego-brick yellow">Restart Python Loop</button>
        <button className="lego-brick orange">Reboot Raspberry Pi</button>
      </div>
    </div>
  </div>
)

function App() {
  const [activeTab, setActiveTab] = useState(0)

  const tabs = [
    { name: "Live Deck", component: <LiveDeck /> },
    { name: "Stage Architect", component: <StageArchitect /> },
    { name: "Topology", component: <TopologyEditor /> },
    { name: "Auto-DJ", component: <AutoDJTuning /> },
    { name: "System", component: <SystemSetup /> }
  ]
  const roguePieces = [
    // Foundational huge plates
    { color: 'dark-blue', col: 8, row: 10, w: 10, h: 8 },
    { color: 'dark-red', col: 28, row: 0, w: 40, h: 4 },
    { color: 'grey', col: 5, row: 15, w: 1, h: 4 },

    // 5x 2x1 pieces
    { color: 'yellow', col: 2, row: 20, w: 2, h: 1 },
    { color: 'green', col: 12, row: 2, w: 2, h: 1 },
    { color: 'dark-red', col: 22, row: 18, w: 2, h: 1 },
    { color: 'dark-blue', col: 5, row: 25, w: 2, h: 1 },
    { color: 'grey', col: 35, row: 12, w: 2, h: 1 },

    // 2x 2x2 pieces
    { color: 'green', col: 18, row: 5, w: 2, h: 2 },
    { color: 'yellow', col: 30, row: 22, w: 2, h: 2 },

    // 4x 3x2 pieces
    { color: 'grey', col: 2, row: 4, w: 3, h: 2 },
    { color: 'dark-blue', col: 15, row: 12, w: 3, h: 2 },
    { color: 'dark-red', col: 25, row: 15, w: 3, h: 2 },
    { color: 'yellow', col: 40, row: 8, w: 3, h: 2 },
  ];

  return (
    <>
      <div className="baseplate-rogue-pieces">
        {roguePieces.map((piece, i) => (
          <div
            key={i}
            className={`rogue-piece ${piece.color}`}
            style={{
              left: `${LEGO_MATH.position(piece.col)}px`,
              top: `${LEGO_MATH.position(piece.row)}px`,
              width: `${LEGO_MATH.physicalSize(piece.w)}px`,
              height: `${LEGO_MATH.physicalSize(piece.h)}px`
            }}
          ></div>
        ))}
      </div>

      <div className="tab-bar">
        {tabs.map((tab, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {tab.name}
          </button>
        ))}
      </div>
      <div className="page-container">
        {tabs[activeTab].component}
      </div>
    </>
  )
}

export default App
