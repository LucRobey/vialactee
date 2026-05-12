import { type MouseEvent } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { MAP_OFFSET_C, MAP_OFFSET_R, type TopologySegment } from '../../constants/topologyData';

const Cable = ({ start, end, cp1, cp2 }: { start: number[]; end: number[]; cp1: number[]; cp2: number[] }) => {
  const sx = LEGO_MATH.physicalSize(start[0]);
  const sy = LEGO_MATH.physicalSize(start[1]);
  const ex = LEGO_MATH.physicalSize(end[0]);
  const ey = LEGO_MATH.physicalSize(end[1]);
  const cx1 = LEGO_MATH.physicalSize(cp1[0]);
  const cy1 = LEGO_MATH.physicalSize(cp1[1]);
  const cx2 = LEGO_MATH.physicalSize(cp2[0]);
  const cy2 = LEGO_MATH.physicalSize(cp2[1]);

  return (
    <>
      <path d={`M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${ex} ${ey}`} stroke="#1a1a1a" strokeWidth="12" fill="none" strokeLinecap="round" filter="url(#drop-shadow-wire)" />
      <path d={`M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${ex} ${ey}`} stroke="rgba(255,255,255,0.15)" strokeWidth="3" fill="none" strokeLinecap="round" transform="translate(-2, -2)" />
      <circle cx={sx} cy={sy} r={14} fill="#2a2d32" stroke="#111" strokeWidth="2" filter="url(#drop-shadow-wire)" />
      <circle cx={sx} cy={sy} r={8} fill="#1a1f24" />
      <circle cx={sx} cy={sy} r={4} fill="#0a0a0a" />
      <circle cx={ex} cy={ey} r={14} fill="#2a2d32" stroke="#111" strokeWidth="2" filter="url(#drop-shadow-wire)" />
      <circle cx={ex} cy={ey} r={8} fill="#1a1f24" />
      <circle cx={ex} cy={ey} r={4} fill="#0a0a0a" />
    </>
  );
};

export const TopologyMap = ({
  segments,
  selectedSegId,
  onSelectSegment,
  onToggleDirection,
}: {
  segments: TopologySegment[];
  selectedSegId: string;
  onSelectSegment: (segmentId: string) => void;
  onToggleDirection: (event: MouseEvent, segmentId: string) => void;
}) => {
  const getModeClass = (modeName: string) => `anim-${modeName.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    <>
      <GridSpot col={MAP_OFFSET_C - 2} row={MAP_OFFSET_R - 3} style={{ zIndex: 0 }}>
        <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(50)}px`, height: `${LEGO_MATH.physicalSize(29)}px`, boxShadow: 'inset 0 0 40px #000' }} />
      </GridSpot>

      <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 2 }}>
        <defs>
          <filter id="drop-shadow-wire" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="3" dy="5" stdDeviation="3" floodColor="#000" floodOpacity="0.7" />
          </filter>
        </defs>
        <Cable start={[2.5, 3]} end={[2.5, 6.5]} cp1={[1, 3]} cp2={[1, 6.5]} />
        <Cable start={[46, 21.5]} end={[21.5, 21.5]} cp1={[46, 26]} cp2={[30, 21.5]} />
        <Cable start={[32, 24.5]} end={[16.5, 26.5]} cp1={[32, 28]} cp2={[16.5, 30]} />
        <Cable start={[23.5, 20]} end={[21.5, 19.5]} cp1={[22, 20]} cp2={[22, 19.5]} />
        <Cable start={[24, 2.5]} end={[16.5, 5.5]} cp1={[24, -0.5]} cp2={[16.5, -0.5]} />
      </svg>

      {segments.map(seg => {
        const isSelected = selectedSegId === seg.id;

        return (
          <GridSpot key={seg.id} col={seg.col} row={seg.row}>
            <div
              className={`rogue-piece interactive-segment ${isSelected ? 'segment-selected' : ''} ${getModeClass(seg.mode)}`}
              onClick={() => onSelectSegment(seg.id)}
              style={{
                zIndex: isSelected ? 20 : 10,
                width: `${LEGO_MATH.physicalSize(seg.w)}px`,
                height: `${LEGO_MATH.physicalSize(seg.h)}px`,
                backgroundColor: seg.color,
                cursor: 'pointer',
                border: isSelected ? '2px solid white' : 'none',
                boxShadow: isSelected ? `0 0 20px ${seg.color}` : 'none'
              }}
            >
              <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', backgroundImage: 'var(--highlight), var(--shadow)', backgroundSize: 'var(--stud) var(--stud)', zIndex: 5 }} />
              <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 6,
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0) 25%, rgba(0,0,0,0) 75%, rgba(0,0,0,0.5) 100%)',
                boxShadow: 'inset 2px 2px 5px rgba(255,255,255,0.6), inset -2px -2px 5px rgba(0,0,0,0.5)',
                borderRadius: '2px'
              }} />
              <div className="rogue-piece" style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: seg.orientation === 'vertical' ? 'translate(-50%, -50%) rotate(-90deg)' : 'translate(-50%, -50%)',
                width: 'calc(6 * var(--stud))',
                height: 'calc(1 * var(--stud))',
                backgroundColor: '#f4f4f4',
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.8) 0%, rgba(0,0,0,0.1) 100%)',
                borderTop: '2px solid rgba(255,255,255,1)',
                borderLeft: '2px solid rgba(255,255,255,0.8)',
                borderBottom: '2px solid rgba(0,0,0,0.5)',
                borderRight: '2px solid rgba(0,0,0,0.3)',
                borderRadius: '2px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 10,
                boxShadow: '2px 2px 5px rgba(0,0,0,0.6), 0 0 15px rgba(0,0,0,0.8)'
              }}>
                <span
                  onClick={(event) => onToggleDirection(event, seg.id)}
                  style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', fontSize: '0.55rem', letterSpacing: '0.5px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <span style={{ fontSize: '0.7rem' }}>{seg.direction === 'UP' ? '▲' : '▼'}</span>
                  {seg.mode.toUpperCase()}
                </span>
              </div>
            </div>
          </GridSpot>
        );
      })}
    </>
  );
};
