import React from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';

export const StageArchitect = () => (
  <div style={{ position: 'relative', width: '100%', height: 'calc(35 * var(--stud))' }}>
    <GridSpot col={8} row={0}>
      <div className="lego-label" style={{ width: 'calc(15 * var(--stud))' }}>STAGE ARCHITECT</div>
    </GridSpot>

    <GridSpot col={6} row={3} style={{ zIndex: 0 }}>
      <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(35)}px`, height: `${LEGO_MATH.physicalSize(25)}px`, boxShadow: 'inset 0 0 40px #000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-dim)', textAlign: 'center' }}>[ Interactive SVG Mapper ]</p>
      </div>
    </GridSpot>

    <GridSpot col={45} row={3}>
      <div className="rogue-piece grey" style={{ width: `${LEGO_MATH.physicalSize(20)}px`, height: `${LEGO_MATH.physicalSize(25)}px` }}></div>
    </GridSpot>

    <GridSpot col={46} row={4}>
      <div className="lego-label" style={{ width: 'calc(18 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-yellow)' }}>DYNAMIC INSPECTOR</div>
    </GridSpot>

    <GridSpot col={46} row={7}>
      <div className="embedded-oled" style={{ width: 'calc(18 * var(--stud))', height: 'calc(5 * var(--stud))', position: 'relative', top: 0, left: 0, transform: 'none', padding: '10px' }}>
        <span className="oled-text" style={{ color: 'white', whiteSpace: 'normal', textAlign: 'center', width: '100%' }}>
          Select a segment to edit...
        </span>
      </div>
    </GridSpot>
  </div>
);
