import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { CONFIGURATOR_OFFSET_C, CONFIGURATOR_OFFSET_R } from '../../constants/topologyData';

export const TopologyConfiguratorShell = () => (
  <>
    <GridSpot col={CONFIGURATOR_OFFSET_C} row={CONFIGURATOR_OFFSET_R}>
      <div className="rogue-piece" style={{
        width: `${LEGO_MATH.physicalSize(20)}px`,
        height: `${LEGO_MATH.physicalSize(22)}px`,
        backgroundColor: '#1b4a22',
        backgroundImage: `
          var(--highlight),
          radial-gradient(circle at 15px 15px, #205527 0%, #205527 7px, rgba(0, 0, 0, 0.5) 9px, transparent 10px),
          var(--shadow)
        `,
        backgroundSize: 'var(--stud) var(--stud)',
        borderTop: '2px solid rgba(255,255,255,0.3)',
        borderLeft: '2px solid rgba(255,255,255,0.2)',
        borderBottom: '2px solid rgba(0,0,0,0.8)',
        borderRight: '2px solid rgba(0,0,0,0.6)',
        borderRadius: '4px',
        boxShadow: '10px 10px 30px rgba(0,0,0,0.8)'
      }} />
    </GridSpot>

    <GridSpot col={CONFIGURATOR_OFFSET_C + 5} row={CONFIGURATOR_OFFSET_R + 0.3} style={{ zIndex: 10 }}>
      <div className="rogue-piece" style={{
        width: 'calc(10 * var(--stud))',
        height: 'calc(1 * var(--stud))',
        backgroundColor: '#fcd000',
        backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(0,0,0,0.1) 100%)',
        borderTop: '2px solid rgba(255,255,255,0.6)',
        borderLeft: '2px solid rgba(255,255,255,0.3)',
        borderBottom: '2px solid rgba(0,0,0,0.4)',
        borderRight: '2px solid rgba(0,0,0,0.2)',
        borderRadius: '2px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '2px 2px 5px rgba(0,0,0,0.5)',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }} />
        <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }} />
        <span style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', letterSpacing: '1px', fontSize: '0.75rem', zIndex: 2 }}>
          CONFIGURATIONS
        </span>
      </div>
    </GridSpot>

    <GridSpot col={CONFIGURATOR_OFFSET_C + 5} row={CONFIGURATOR_OFFSET_R + 13.3} style={{ zIndex: 10 }}>
      <div className="rogue-piece" style={{
        width: 'calc(10 * var(--stud))',
        height: 'calc(1 * var(--stud))',
        backgroundColor: '#fcd000',
        backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(0,0,0,0.1) 100%)',
        borderTop: '2px solid rgba(255,255,255,0.6)',
        borderLeft: '2px solid rgba(255,255,255,0.3)',
        borderBottom: '2px solid rgba(0,0,0,0.4)',
        borderRight: '2px solid rgba(0,0,0,0.2)',
        borderRadius: '2px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '2px 2px 5px rgba(0,0,0,0.5)',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }} />
        <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }} />
        <span style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', letterSpacing: '1px', fontSize: '0.75rem', zIndex: 2 }}>
          PLAYLISTS
        </span>
      </div>
    </GridSpot>

    {[{ c: 0, r: 0 }, { c: 19, r: 0 }, { c: 0, r: 21 }, { c: 19, r: 21 }].map((pos, i) => (
      <GridSpot key={`pin-${i}`} col={CONFIGURATOR_OFFSET_C + pos.c} row={CONFIGURATOR_OFFSET_R + pos.r} style={{ zIndex: 2 }}>
        <div style={{ width: '30px', height: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            width: '18px',
            height: '18px',
            borderRadius: '50%',
            backgroundColor: '#1a1a1a',
            boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.3), inset -2px -2px 4px rgba(0,0,0,0.8), 2px 2px 3px rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <div style={{ position: 'relative', width: '10px', height: '10px' }}>
              <div style={{ position: 'absolute', top: '3.5px', left: '0px', width: '10px', height: '3px', backgroundColor: '#050505', boxShadow: 'inset 1px 1px 1px rgba(0,0,0,1)' }} />
              <div style={{ position: 'absolute', top: '0px', left: '3.5px', width: '3px', height: '10px', backgroundColor: '#050505', boxShadow: 'inset 1px 1px 1px rgba(0,0,0,1)' }} />
            </div>
          </div>
        </div>
      </GridSpot>
    ))}
  </>
);
