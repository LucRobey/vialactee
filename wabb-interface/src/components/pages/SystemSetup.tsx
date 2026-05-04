import React from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';

export const SystemSetup = () => (
  <div style={{ position: 'relative', width: '100%', height: 'calc(35 * var(--stud))' }}>
    <GridSpot col={8} row={0}>
      <div className="lego-label" style={{ width: 'calc(15 * var(--stud))' }}>SYSTEM & SETUP</div>
    </GridSpot>

    {/* Telemetry Baseplate */}
    <GridSpot col={6} row={3}>
      <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(30)}px`, height: `${LEGO_MATH.physicalSize(25)}px` }}></div>
    </GridSpot>

    <GridSpot col={7} row={4}>
      <div className="lego-label" style={{ width: 'calc(28 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-green)' }}>TELEMETRY</div>
    </GridSpot>

    <GridSpot col={7} row={7}>
      <div className="embedded-oled" style={{ width: 'calc(13 * var(--stud))', height: 'calc(6 * var(--stud))', position: 'relative', top: 0, left: 0, transform: 'none', display: 'flex', flexDirection: 'column', padding: '10px' }}>
        <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 'bold' }}>CPU TEMP</span>
        <span className="digital-font" style={{ color: 'var(--lego-orange)', fontSize: '2.5rem', textShadow: '0 0 10px var(--lego-orange)', marginTop: 'auto' }}>65°C</span>
      </div>
    </GridSpot>

    <GridSpot col={22} row={7}>
      <div className="embedded-oled" style={{ width: 'calc(13 * var(--stud))', height: 'calc(6 * var(--stud))', position: 'relative', top: 0, left: 0, transform: 'none', display: 'flex', flexDirection: 'column', padding: '10px' }}>
        <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 'bold' }}>PYTHON LOOP</span>
        <span className="digital-font" style={{ color: 'var(--lego-green)', fontSize: '2.5rem', textShadow: '0 0 10px var(--lego-green)', marginTop: 'auto' }}>60 FPS</span>
      </div>
    </GridSpot>

    {/* Danger Zone Baseplate */}
    <GridSpot col={40} row={3}>
      <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(25)}px`, height: `${LEGO_MATH.physicalSize(25)}px` }}></div>
    </GridSpot>

    <GridSpot col={41} row={4}>
      <div className="lego-label" style={{ width: 'calc(23 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-red)' }}>DANGER ZONE</div>
    </GridSpot>

    <GridSpot col={41} row={7}>
      <button className="rogue-piece yellow" style={{ width: 'calc(23 * var(--stud))', height: 'calc(3 * var(--stud))', fontSize: '1.2rem', fontWeight: 'bold', cursor: 'pointer', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--shadow)' }}>
        RESTART PYTHON LOOP
      </button>
    </GridSpot>

    <GridSpot col={41} row={12}>
      <button className="rogue-piece orange" style={{ width: 'calc(23 * var(--stud))', height: 'calc(3 * var(--stud))', fontSize: '1.2rem', fontWeight: 'bold', cursor: 'pointer', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--shadow)' }}>
        REBOOT RASPBERRY PI
      </button>
    </GridSpot>

  </div>
);
