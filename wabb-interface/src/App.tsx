import { useState } from 'react'
import './index.css'
import { LEGO_MATH } from './utils/legoMath'

import { LiveDeck } from './components/pages/LiveDeck'
import { StageArchitect } from './components/pages/StageArchitect'
import { TopologyEditor } from './components/pages/TopologyEditor'
import { ModeSettings } from './components/pages/ModeSettings'
import { SystemSetup } from './components/pages/SystemSetup'

function App() {
  const [activeTab, setActiveTab] = useState(0)

  const tabs = [
    { name: "Live Deck", component: <LiveDeck /> },
    { name: "Stage Architect", component: <StageArchitect /> },
    { name: "Topology", component: <TopologyEditor /> },
    { name: "Mode Settings", component: <ModeSettings /> },
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
        <div className="brand-container">
          <img src="/vialactee.png" alt="Vialactée" className="brand-vialactee" />
          <span className="brand-by">by</span>
          <img src="/luminos.png" alt="Luminos" className="brand-luminos" />
        </div>
        <div className="tab-group">
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
      </div>
      <div className="page-container">
        {tabs[activeTab].component}
      </div>
    </>
  )
}

export default App
