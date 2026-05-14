import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { INSPECTOR_OFFSET_C, INSPECTOR_OFFSET_R } from '../../constants/topologyData';
import type { EditorMode } from './types';

export const TopologyEditorModeSwitch = ({
  editorMode,
  onModeChange,
  availableModes = ['LIVE', 'MODIFY', 'BUILD'],
}: {
  editorMode: EditorMode;
  onModeChange: (mode: EditorMode) => void;
  availableModes?: readonly EditorMode[];
}) => {
  if (availableModes.length <= 1) {
    return null;
  }
  return (
  <>
    <GridSpot col={INSPECTOR_OFFSET_C + 31} row={INSPECTOR_OFFSET_R + 5} style={{ zIndex: 10 }}>
      <div className="rogue-piece" style={{
        width: `${LEGO_MATH.physicalSize(7)}px`,
        height: `${LEGO_MATH.physicalSize(6)}px`,
        backgroundColor: '#fcd000',
        backgroundImage: `
          var(--highlight),
          radial-gradient(circle at 15px 15px, #ffcd00 0%, #ffcd00 7px, rgba(0, 0, 0, 0.5) 9px, transparent 10px),
          var(--shadow)
        `,
        backgroundSize: 'var(--stud) var(--stud)',
        borderTop: '2px solid rgba(255,255,255,0.3)',
        borderLeft: '2px solid rgba(255,255,255,0.2)',
        borderBottom: '2px solid rgba(0,0,0,0.8)',
        borderRight: '2px solid rgba(0,0,0,0.6)',
        borderRadius: '4px',
        boxShadow: '6px 6px 15px rgba(0,0,0,0.8)'
      }} />
    </GridSpot>

    {[{ c: 10, r: -12 }, { c: 16, r: -12 }, { c: 10, r: -7 }, { c: 16, r: -7 }].map((pos, i) => (
      <GridSpot key={`green-pin-${i}`} col={INSPECTOR_OFFSET_C + 21 + pos.c} row={INSPECTOR_OFFSET_R + 17 + pos.r} style={{ zIndex: 11 }}>
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

    <GridSpot col={INSPECTOR_OFFSET_C + 32} row={INSPECTOR_OFFSET_R + 5} style={{ zIndex: 15 }}>
      <div style={{
        width: `${LEGO_MATH.physicalSize(5)}px`,
        height: `${LEGO_MATH.physicalSize(6)}px`,
        backgroundColor: '#0a0a0a',
        border: 'calc(0.4 * var(--stud)) solid #2a2d32',
        borderTopColor: '#3a3f44',
        borderBottomColor: '#1a1f24',
        borderLeftColor: '#30353a',
        borderRightColor: '#20252a',
        borderRadius: '4px',
        boxShadow: 'inset 4px 4px 15px rgba(0,0,0,0.9), 2px 2px 5px rgba(0,0,0,0.5)',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-evenly',
        padding: '5px 0'
      }}>
        {availableModes.map(mode => (
          <div
            key={mode}
            onClick={() => onModeChange(mode)}
            style={{
              width: '85%',
              textAlign: 'center',
              padding: '6px 0',
              backgroundColor: editorMode === mode ? (mode === 'LIVE' ? '#28a745' : mode === 'BUILD' ? '#d22020' : '#fcd000') : '#111',
              color: editorMode === mode ? '#000' : '#888',
              fontWeight: '900',
              fontSize: '0.65rem',
              cursor: 'pointer',
              borderRadius: '2px',
              boxShadow: editorMode === mode ? `0 0 10px ${mode === 'LIVE' ? '#28a745' : mode === 'BUILD' ? '#d22020' : '#fcd000'}, inset 2px 2px 4px rgba(255,255,255,0.4)` : 'inset 2px 2px 5px #000',
              border: '1px solid rgba(0,0,0,0.8)',
              transition: 'all 0.2s ease'
            }}
          >
            {mode}
          </div>
        ))}
      </div>
    </GridSpot>
  </>
  );
};
