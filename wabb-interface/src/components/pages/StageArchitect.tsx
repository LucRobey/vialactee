import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { NoticeBanner } from '../common/NoticeBanner';

export const StageArchitect = () => (
  <div style={{ position: 'relative', width: '100%', height: 'calc(35 * var(--stud))' }}>
    <GridSpot col={8} row={0}>
      <div className="lego-label" style={{ width: 'calc(18 * var(--stud))' }}>STAGE ARCHITECT [WIP]</div>
    </GridSpot>

    <div style={{ position: 'absolute', top: '72px', left: '210px', width: '520px', zIndex: 20 }}>
      <NoticeBanner tone="warning" title="WORK IN PROGRESS">
        This page is intentionally marked incomplete. Use `Topology`, `Mode Settings`, and `System` for live control until the interactive stage mapper is implemented.
      </NoticeBanner>
    </div>

    <GridSpot col={6} row={3} style={{ zIndex: 0 }}>
      <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(35)}px`, height: `${LEGO_MATH.physicalSize(25)}px`, boxShadow: 'inset 0 0 40px #000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--text-dim)', textAlign: 'center', maxWidth: '280px', lineHeight: 1.5 }}>
          [ Interactive SVG mapper coming soon ]
        </p>
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
          Stage Architect is not wired yet.
        </span>
      </div>
    </GridSpot>
  </div>
);
