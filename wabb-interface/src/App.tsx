import { useMemo, useState } from 'react'
import './index.css'
import { LEGO_MATH } from './utils/legoMath'
import { useBridgeStatus } from './utils/useBridgeStatus'
import { NoticeBanner } from './components/common/NoticeBanner'

import { LiveDeck } from './components/pages/LiveDeck'
import { StageArchitect } from './components/pages/StageArchitect'
import { TopologyEditor } from './components/pages/TopologyEditor'
import { Configurator } from './components/pages/Configurator'
import { ModeSettings } from './components/pages/ModeSettings'
import { SystemSetup } from './components/pages/SystemSetup'

const TOPOLOGY_LIVE_MODES = ['LIVE'] as const

const ROGUE_PIECES = [
  { color: 'dark-blue', col: 8, row: 10, w: 10, h: 8 },
  { color: 'dark-red', col: 28, row: 0, w: 40, h: 4 },
  { color: 'grey', col: 5, row: 15, w: 1, h: 4 },
  { color: 'yellow', col: 2, row: 20, w: 2, h: 1 },
  { color: 'green', col: 12, row: 2, w: 2, h: 1 },
  { color: 'dark-red', col: 22, row: 18, w: 2, h: 1 },
  { color: 'dark-blue', col: 5, row: 25, w: 2, h: 1 },
  { color: 'grey', col: 35, row: 12, w: 2, h: 1 },
  { color: 'green', col: 18, row: 5, w: 2, h: 2 },
  { color: 'yellow', col: 30, row: 22, w: 2, h: 2 },
  { color: 'grey', col: 2, row: 4, w: 3, h: 2 },
  { color: 'dark-blue', col: 15, row: 12, w: 3, h: 2 },
  { color: 'dark-red', col: 25, row: 15, w: 3, h: 2 },
  { color: 'yellow', col: 40, row: 8, w: 3, h: 2 },
] as const;

function App() {
  const [activeTab, setActiveTab] = useState(0)
  const bridgeStatus = useBridgeStatus()

  const tabs = useMemo(() => ([
    { name: 'Live Deck', component: <LiveDeck /> },
    { name: 'Stage Architect [WIP]', component: <StageArchitect /> },
    { name: 'Topology', component: <TopologyEditor allowedModes={TOPOLOGY_LIVE_MODES} /> },
    { name: 'Configurator', component: <Configurator /> },
    { name: 'Mode Settings', component: <ModeSettings /> },
    { name: 'System', component: <SystemSetup /> },
  ]), [])

  const connectionIndicator = {
    label: bridgeStatus === 'open'
      ? 'LIVE'
      : bridgeStatus === 'connecting'
        ? 'CONNECTING'
        : 'OFFLINE',
    color: bridgeStatus === 'open'
      ? '#48bb78'
      : bridgeStatus === 'connecting'
        ? '#f6ad55'
        : '#fc8181',
  }

  return (
    <>
      <div className="baseplate-rogue-pieces">
        {ROGUE_PIECES.map((piece) => (
          <div
            key={`${piece.color}-${piece.col}-${piece.row}`}
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
              key={tab.name}
              className={`tab ${activeTab === index ? 'active' : ''}`}
              onClick={() => setActiveTab(index)}
            >
              {tab.name}
            </button>
          ))}
        </div>
        <div
          style={{
            marginLeft: '16px',
            padding: '8px 12px',
            borderRadius: '999px',
            border: `1px solid ${connectionIndicator.color}`,
            color: '#f7fafc',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: `0 0 12px rgba(0,0,0,0.35), 0 0 10px ${connectionIndicator.color}33`,
            background: 'rgba(8, 12, 16, 0.84)',
            fontWeight: 800,
            letterSpacing: '0.08em',
            fontSize: '0.75rem',
          }}
        >
          <span
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: connectionIndicator.color,
              boxShadow: `0 0 8px ${connectionIndicator.color}`,
            }}
          />
          {connectionIndicator.label}
        </div>
      </div>
      {bridgeStatus !== 'open' ? (
        <div style={{ position: 'relative', zIndex: 30, margin: '12px 18px 0' }}>
          <NoticeBanner tone={bridgeStatus === 'connecting' ? 'warning' : 'error'} title="BACKEND STATUS">
            {bridgeStatus === 'connecting'
              ? 'Reconnecting to the Python controller. Live values may be stale for a moment.'
              : 'The controller is offline. Live data will stay stale and queued commands may not apply until the bridge reconnects.'}
          </NoticeBanner>
        </div>
      ) : null}
      <div className="page-container">
        {tabs[activeTab].component}
      </div>
    </>
  )
}

export default App
