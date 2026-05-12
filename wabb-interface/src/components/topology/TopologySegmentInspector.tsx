import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { INSPECTOR_OFFSET_C, INSPECTOR_OFFSET_R, type TopologySegment } from '../../constants/topologyData';

export const TopologySegmentInspector = ({
  selectedSeg,
  availableModes,
  onModeSelect,
}: {
  selectedSeg: TopologySegment;
  availableModes: string[];
  onModeSelect: (modeName: string) => void;
}) => (
  <>
    <GridSpot col={INSPECTOR_OFFSET_C + 5} row={INSPECTOR_OFFSET_R + 3} style={{ zIndex: 10 }}>
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
        <span style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', letterSpacing: '1px', fontSize: '0.8rem', zIndex: 2 }}>
          SYSTEM MODES
        </span>
      </div>
    </GridSpot>

    <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 1} style={{ zIndex: 10 }}>
      <div style={{ width: 'calc(18 * var(--stud))', height: 'calc(1 * var(--stud))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {Array.from({ length: 18 }).map((_, index) => {
          const name = selectedSeg.name.toUpperCase().replace('_', ' ');
          const startIdx = Math.floor((18 - name.length) / 2);
          const char = (index >= startIdx && index < startIdx + name.length) ? name[index - startIdx] : '';
          const angle = (Math.sin(index * 13.37) * 3.5).toFixed(1);

          return (
            <div key={`segment-name-${index}`} className="rogue-piece" style={{
              position: 'relative',
              transform: `rotate(${angle}deg)`,
              width: 'calc(1 * var(--stud))',
              height: 'calc(1 * var(--stud))',
              backgroundColor: '#4a4f54',
              backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(0,0,0,0.2) 100%)',
              borderTop: '2px solid rgba(255,255,255,0.3)',
              borderLeft: '2px solid rgba(255,255,255,0.1)',
              borderBottom: '2px solid rgba(0,0,0,0.6)',
              borderRight: '2px solid rgba(0,0,0,0.4)',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: selectedSeg.color,
              fontWeight: 'bold',
              textShadow: char !== ' ' && char !== '' ? '1px 1px 2px #000' : 'none',
              boxShadow: '1px 1px 3px rgba(0,0,0,0.5)',
              boxSizing: 'border-box'
            }}>
              {char !== ' ' ? char : ''}
            </div>
          );
        })}
      </div>
    </GridSpot>

    <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 2} style={{ zIndex: 10 }}>
      <div style={{ width: 'calc(18 * var(--stud))', height: 'calc(1 * var(--stud))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {Array.from({ length: 18 }).map((_, index) => {
          const text = `MODE: ${selectedSeg.mode.toUpperCase()}`;
          const startIdx = Math.max(0, Math.floor((18 - text.length) / 2));
          const char = (index >= startIdx && index < startIdx + text.length) ? text[index - startIdx] : '';
          const angle = (Math.sin((index + 18) * 17.43) * 3.5).toFixed(1);
          const isModeText = index >= startIdx + 6;
          const textColor = isModeText ? 'var(--lego-yellow)' : 'white';
          const shadowColor = isModeText ? 'var(--lego-yellow)' : 'rgba(255,255,255,0.5)';

          return (
            <div key={`segment-mode-${index}`} className="rogue-piece" style={{
              position: 'relative',
              transform: `rotate(${angle}deg)`,
              width: 'calc(1 * var(--stud))',
              height: 'calc(1 * var(--stud))',
              backgroundColor: '#111',
              backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(0,0,0,0.4) 100%)',
              borderTop: '2px solid rgba(255,255,255,0.2)',
              borderLeft: '2px solid rgba(255,255,255,0.1)',
              borderBottom: '2px solid rgba(0,0,0,0.8)',
              borderRight: '2px solid rgba(0,0,0,0.6)',
              borderRadius: '2px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: textColor,
              fontWeight: 'bold',
              fontFamily: 'monospace',
              fontSize: '1.1rem',
              textShadow: char !== ' ' && char !== '' ? `0 0 8px ${shadowColor}` : 'none',
              boxShadow: '1px 1px 4px rgba(0,0,0,0.8)',
              boxSizing: 'border-box'
            }}>
              {char !== ' ' ? char : ''}
            </div>
          );
        })}
      </div>
    </GridSpot>

    <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 4} style={{ zIndex: 5 }}>
      <div className="custom-scrollbar" style={{
        width: `${LEGO_MATH.physicalSize(18)}px`,
        height: `${LEGO_MATH.physicalSize(8)}px`,
        backgroundColor: '#0a0a0a',
        border: 'calc(0.4 * var(--stud)) solid #2a2d32',
        borderTopColor: '#3a3f44',
        borderBottomColor: '#1a1f24',
        borderLeftColor: '#30353a',
        borderRightColor: '#20252a',
        borderRadius: '4px',
        boxShadow: 'inset 4px 4px 15px rgba(0,0,0,0.9), 2px 2px 5px rgba(0,0,0,0.5)',
        boxSizing: 'border-box',
        padding: '10px',
        display: 'flex',
        flexWrap: 'wrap',
        alignContent: 'flex-start',
        gap: '10px 8px',
        overflowY: 'auto'
      }}>
        {availableModes.map((mode) => {
          const isCurrent = mode === selectedSeg.mode;
          return (
            <div key={mode} style={{ display: 'flex', gap: '6px', alignItems: 'center', cursor: 'pointer', width: 'calc(50% - 5px)' }} onClick={() => onModeSelect(mode)}>
              <div style={{
                width: '14px',
                height: '14px',
                borderRadius: '50%',
                flexShrink: 0,
                backgroundColor: isCurrent ? selectedSeg.color : '#222',
                boxShadow: isCurrent ? `0 0 10px ${selectedSeg.color}, inset 2px 2px 4px rgba(255,255,255,0.8)` : 'inset 2px 2px 4px rgba(0,0,0,0.8), 1px 1px 2px rgba(255,255,255,0.1)',
                border: '1px solid rgba(0,0,0,0.5)',
              }} />
              <div className="rogue-piece" style={{
                position: 'relative',
                width: 'calc(6.8 * var(--stud))',
                height: 'calc(1 * var(--stud))',
                backgroundColor: isCurrent ? '#fcd000' : '#1b2a3a',
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(0,0,0,0.2) 100%)',
                borderTop: '2px solid rgba(255,255,255,0.4)',
                borderLeft: '2px solid rgba(255,255,255,0.2)',
                borderBottom: '2px solid rgba(0,0,0,0.8)',
                borderRight: '2px solid rgba(0,0,0,0.6)',
                borderRadius: '2px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isCurrent ? '#000' : '#fff',
                fontSize: '0.55rem',
                fontWeight: 'bold',
                textShadow: isCurrent ? 'none' : '1px 1px 2px rgba(0,0,0,0.8)',
                boxShadow: '2px 2px 4px rgba(0,0,0,0.6)',
                boxSizing: 'border-box',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {mode.toUpperCase()}
              </div>
            </div>
          );
        })}
      </div>
    </GridSpot>
  </>
);
