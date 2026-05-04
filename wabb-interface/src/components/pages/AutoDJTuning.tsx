import React from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';

export const AutoDJTuning = () => (
  <div style={{ position: 'relative', width: '100%', height: 'calc(35 * var(--stud))' }}>
    <GridSpot col={8} row={0}>
      <div className="lego-label" style={{ width: 'calc(15 * var(--stud))' }}>AUTO-DJ TUNING</div>
    </GridSpot>

    <GridSpot col={6} row={3}>
      <div className="rogue-piece dark-blue" style={{ width: `${LEGO_MATH.physicalSize(30)}px`, height: `${LEGO_MATH.physicalSize(25)}px` }}></div>
    </GridSpot>

    <GridSpot col={7} row={4}>
      <div className="lego-label" style={{ width: 'calc(28 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-cyan)' }}>MODE CONFIGURATION FRAME</div>
    </GridSpot>

    {/* Rainbow Mode settings */}
    <GridSpot col={7} row={7}>
      <div className="flat-lego-tile" style={{ width: 'calc(28 * var(--stud))', height: 'calc(4 * var(--stud))' }}>
        <div className="tile-label" style={{ fontSize: '1rem', color: '#fff', marginBottom: '10px' }}>🌈 RAINBOW MODE - Color Density</div>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          <input type="range" min="0" max="100" defaultValue="50" style={{ width: '100%', accentColor: 'var(--lego-cyan)' }} />
        </div>
      </div>
    </GridSpot>

    {/* Pulsar Mode settings */}
    <GridSpot col={7} row={13}>
      <div className="flat-lego-tile" style={{ width: 'calc(28 * var(--stud))', height: 'calc(4 * var(--stud))' }}>
        <div className="tile-label" style={{ fontSize: '1rem', color: '#fff', marginBottom: '10px' }}>☄️ PULSAR MODE - Tail Length</div>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          <input type="range" min="0" max="100" defaultValue="70" style={{ width: '100%', accentColor: 'var(--lego-cyan)' }} />
        </div>
      </div>
    </GridSpot>

    {/* Global Automation area */}
    <GridSpot col={40} row={3}>
      <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(25)}px`, height: `${LEGO_MATH.physicalSize(25)}px` }}></div>
    </GridSpot>

    <GridSpot col={41} row={4}>
      <div className="lego-label" style={{ width: 'calc(23 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-purple)' }}>GLOBAL AUTOMATION</div>
    </GridSpot>

    <GridSpot col={41} row={7}>
      <div className="flat-lego-tile" style={{ width: 'calc(23 * var(--stud))', height: 'calc(4 * var(--stud))' }}>
        <div className="tile-label" style={{ fontSize: '1rem', color: '#fff', marginBottom: '10px' }}>TRIGGER INTERVAL</div>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          <input type="range" min="0" max="100" defaultValue="30" style={{ width: '100%', accentColor: 'var(--lego-purple)' }} />
        </div>
      </div>
    </GridSpot>

    <GridSpot col={41} row={13}>
      <div className="flat-lego-tile" style={{ width: 'calc(23 * var(--stud))', height: 'calc(4 * var(--stud))' }}>
        <div className="tile-label" style={{ fontSize: '1rem', color: '#fff', marginBottom: '10px' }}>SWEEP DURATION</div>
        <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
          <input type="range" min="0" max="100" defaultValue="45" style={{ width: '100%', accentColor: 'var(--lego-purple)' }} />
        </div>
      </div>
    </GridSpot>
  </div>
);
