import React, { useCallback, useEffect, useRef, useState } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { FitBoard } from '../layout/FitBoard';
import { GridSpot } from '../layout/GridSpot';
import { NoticeBanner } from '../common/NoticeBanner';
import { sendInstruction, subscribeModeMasterState, type SystemStatus } from '../../utils/controlBridge';
import { useBridgeStatus } from '../../utils/useBridgeStatus';
import {
  buildDropWordPlacements,
  DROP_WORD_HEIGHT_STUDS,
  DROP_WORD_WIDTH_STUDS,
} from '../../constants/dropLetterTiles';

const DROP_TILE_PLACEMENTS = buildDropWordPlacements();

/** Matches `.giant-drop-button::before` inset and container width. */
const DROP_BUTTON_INSET_PX = 9;
const DROP_BUTTON_WIDTH_PX = 900;
/** 8 studs tall (+1 stud row vs prior 7-stud brick). */
const DROP_BUTTON_HEIGHT_PX = LEGO_MATH.grid(8);
/** Half-stud clip on bottom/right so cut studs show at the edge. */
const DROP_BUTTON_CROP_PX = LEGO_MATH.STUD / 2;
const DROP_STUD_COLS = Math.floor(
  (DROP_BUTTON_WIDTH_PX - DROP_BUTTON_INSET_PX * 2) / LEGO_MATH.STUD,
);
const DROP_STUD_ROWS = Math.floor(
  (DROP_BUTTON_HEIGHT_PX - DROP_BUTTON_INSET_PX * 2) / LEGO_MATH.STUD,
);
const DROP_LETTER_START_COL = Math.floor((DROP_STUD_COLS - DROP_WORD_WIDTH_STUDS) / 2);
const DROP_LETTER_START_ROW = Math.floor((DROP_STUD_ROWS - DROP_WORD_HEIGHT_STUDS) / 2);

const EMPTY_SYSTEM: Pick<SystemStatus, 'cpuTempC' | 'dynamicAudioLatencyMs'> = {
  cpuTempC: null,
  dynamicAudioLatencyMs: null,
};
const BOARD_WIDTH = LEGO_MATH.grid(74);
const BOARD_HEIGHT = LEGO_MATH.physicalSize(37);

const MOOD_PALETTES = [
  { name: 'Cyberpunk', colorClass: 'bg-cyan', accent: '#00f0ff' },
  { name: 'Solar Ember', colorClass: 'bg-orange', accent: '#ff8c00' },
  { name: 'Deep Ocean', colorClass: 'bg-blue', accent: '#00c8b4' },
  { name: 'Ethereal', colorClass: 'bg-purple', accent: '#b482ff' },
  { name: 'Neon Acid', colorClass: 'bg-green', accent: '#39ff14' },
  { name: 'Monochrome Chrome', colorClass: 'bg-chrome', accent: '#b0b8c0' },
] as const;

const formatTelemetryValue = (value: number | null, suffix: string, digits = 0) => {
  if (value === null || Number.isNaN(value)) {
    return '--';
  }
  return `${value.toFixed(digits)}${suffix}`;
};

const formatLatencyTelemetryValue = (value: number | null) => {
  if (value === null || Number.isNaN(value) || value < 0 || value > 5000) {
    return '--';
  }
  return `${value.toFixed(0)}ms`;
};

export const LiveDeck = () => {
  const [lumValue, setLumValue] = useState(60);
  const [sensValue, setSensValue] = useState(70);
  const [autoTimeValue, setAutoTimeValue] = useState(20);
  const [isHold, setIsHold] = useState(false);
  const [selectedTransition, setSelectedTransition] = useState('CUT');
  const [currentMood, setCurrentMood] = useState('Cyberpunk');
  const [currentConfiguration, setCurrentConfiguration] = useState('Live Random DNA');
  const [systemTelemetry, setSystemTelemetry] = useState(EMPTY_SYSTEM);
  const bridgeStatus = useBridgeStatus();

  const isDraggingRef = useRef<{ lum: boolean; sens: boolean; autoTime: boolean }>({
    lum: false,
    sens: false,
    autoTime: false,
  });
  const dragReleaseTimerRef = useRef<{ lum: number | null; sens: number | null; autoTime: number | null }>({
    lum: null,
    sens: null,
    autoTime: null,
  });
  const throttleTimerRef = useRef<{ lum: number | null; sens: number | null; autoTime: number | null }>({
    lum: null,
    sens: null,
    autoTime: null,
  });

  const sendThrottledSlider = useCallback((
    action: 'set_luminosity' | 'set_sensibility' | 'set_auto_transition_time',
    key: 'lum' | 'sens' | 'autoTime',
    value: number
  ) => {
    if (throttleTimerRef.current[key] !== null) {
      window.clearTimeout(throttleTimerRef.current[key]!);
    }
    throttleTimerRef.current[key] = window.setTimeout(() => {
      sendInstruction({ page: 'live_deck', action, payload: { value } });
      throttleTimerRef.current[key] = null;
    }, 60);
  }, []);

  const transitions = ['CUT', 'FADE IN/OUT', 'CROSSFADE'];

  useEffect(() => {
    return subscribeModeMasterState((state) => {
      if (!isDraggingRef.current.lum) {
        setLumValue(state.luminosity);
      }
      if (!isDraggingRef.current.sens) {
        setSensValue(state.sensibility);
      }
      if (!isDraggingRef.current.autoTime) {
        setAutoTimeValue(state.autoTransitionTime);
      }
      setIsHold(state.transitionLocked);
      setSelectedTransition(state.selectedTransition);

      if (state.activeMood) {
        setCurrentMood(state.activeMood);
      }
      if (state.activeConfiguration) {
        setCurrentConfiguration(state.activeConfiguration);
      }
      setSystemTelemetry({
        cpuTempC: state.system?.cpuTempC ?? null,
        dynamicAudioLatencyMs: state.system?.dynamicAudioLatencyMs ?? null,
      });
    });
  }, []);

  return (
    <FitBoard width={BOARD_WIDTH} height={BOARD_HEIGHT}>
      <div className="live-deck-grid" style={{ width: `${BOARD_WIDTH}px`, height: `${BOARD_HEIGHT}px` }}>
      {bridgeStatus !== 'open' ? (
        <div style={{ position: 'absolute', top: '100px', left: '240px', width: '560px', zIndex: 50 }}>
          <NoticeBanner tone={bridgeStatus === 'connecting' ? 'warning' : 'error'} title="LIVE DATA STATUS">
            {bridgeStatus === 'connecting'
              ? 'Reconnecting to the controller. Telemetry state may lag for a few seconds.'
              : 'Controller offline. Controls may queue locally, but the show state cannot be confirmed right now.'}
          </NoticeBanner>
        </div>
      ) : null}

      {/* ======================= RIGHT SLIDER RACK ======================= */}
      <GridSpot col={55} row={0}>
        <div style={{
          width: `${LEGO_MATH.physicalSize(18)}px`,
          height: `${LEGO_MATH.physicalSize(14)}px`,
          backgroundColor: '#1a1f24',
          borderTop: '8px solid #2a2d32',
          borderLeft: '8px solid #20252a',
          borderBottom: '8px solid #0a0a0a',
          borderRight: '8px solid #0f0f0f',
          boxShadow: '10px 10px 25px rgba(0,0,0,0.9), 0 0 0 2px #000',
          borderRadius: '4px',
          position: 'absolute',
          zIndex: 10,
          boxSizing: 'border-box'
        }}>
          {/* Deep dark pit spanning the slider trio */}
          <div style={{
            position: 'absolute',
            top: '15px', bottom: '15px', left: '15px', right: '15px',
            backgroundColor: '#0a0d12',
            borderRadius: '4px',
            boxShadow: 'inset 10px 10px 20px rgba(0,0,0,0.95), inset -5px -5px 15px rgba(0,0,0,0.8), 0 2px 2px rgba(255,255,255,0.1)'
          }}>
            {/* LUMINOSITÉ BLOCK */}
            <div style={{ position: 'absolute', top: '10px', left: '18px', width: '130px', height: '310px' }}>
              {/* Centered Label */}
              <div className="rogue-piece" style={{
                position: 'absolute', top: '0', left: '50%', transform: 'translateX(-50%)',
                width: '120px', height: '30px', backgroundColor: '#f4f4f4',
                borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
                display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '2px 5px 10px rgba(0,0,0,0.7)', borderRadius: '2px', zIndex: 5
              }}>
                <span style={{ color: '#000', fontWeight: '900', fontSize: '0.65rem', letterSpacing: '1px' }}>LUMINOSITÉ</span>
              </div>
              {/* Slider Mechanism */}
              <div className="slider-container-group" style={{ position: 'absolute', top: '40px', right: '10px', width: '90px', '--slider-val': lumValue } as React.CSSProperties}>
                <div className="absurd-slider-mechanism">
                  <div className="technic-beam beam-1"></div>
                  <div className="technic-beam beam-2"></div>
                  <div className="guide-rail rail-1"></div>
                  <div className="guide-rail rail-3"></div>
                  <div className="rail-mount mount-1"></div>
                  <div className="rail-mount mount-2"></div>
                  <div className="rail-mount mount-3"></div>
                  <div className="absurd-weight weight-drop-1"></div>
                  <div className="absurd-gear gear-spin-1"></div>
                  <div className="absurd-gear gear-spin-2"></div>
                </div>
                <div className="lego-slider">
                  <div className="slider-track-wrap">
                    <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
                    <div className="slider-track-groove">
                      <input
                        type="range"
                        className="vertical-slider"
                        min="1"
                        max="100"
                        value={lumValue}
                        onPointerDown={() => {
                          isDraggingRef.current.lum = true;
                          if (dragReleaseTimerRef.current.lum !== null) {
                            window.clearTimeout(dragReleaseTimerRef.current.lum);
                            dragReleaseTimerRef.current.lum = null;
                          }
                        }}
                        onPointerUp={() => {
                          dragReleaseTimerRef.current.lum = window.setTimeout(() => {
                            isDraggingRef.current.lum = false;
                            dragReleaseTimerRef.current.lum = null;
                          }, 400);
                        }}
                        onChange={e => {
                          const value = Number(e.target.value);
                          setLumValue(value);
                          isDraggingRef.current.lum = true;
                          sendThrottledSlider('set_luminosity', 'lum', value);
                        }}
                      />
                    </div>
                    <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* SENSIBILITÉ BLOCK */}
            <div style={{ position: 'absolute', top: '10px', left: '188px', width: '130px', height: '310px' }}>
              {/* Centered Label */}
              <div className="rogue-piece" style={{
                position: 'absolute', top: '0', left: '50%', transform: 'translateX(-50%)',
                width: '120px', height: '30px', backgroundColor: '#f4f4f4',
                borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
                display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '2px 5px 10px rgba(0,0,0,0.7)', borderRadius: '2px', zIndex: 5
              }}>
                <span style={{ color: '#000', fontWeight: '900', fontSize: '0.65rem', letterSpacing: '1px' }}>SENSIBILITÉ</span>
              </div>
              {/* Slider Mechanism */}
              <div className="slider-container-group" style={{ position: 'absolute', top: '40px', right: '10px', width: '90px', '--slider-val': sensValue } as React.CSSProperties}>
                <div className="absurd-slider-mechanism">
                  <div className="technic-beam beam-1"></div>
                  <div className="technic-beam beam-2"></div>
                  <div className="guide-rail rail-1"></div>
                  <div className="guide-rail rail-3"></div>
                  <div className="rail-mount mount-1"></div>
                  <div className="rail-mount mount-2"></div>
                  <div className="rail-mount mount-3"></div>
                  <div className="absurd-weight weight-drop-green"></div>
                  <div className="absurd-gear gear-spin-1"></div>
                  <div className="absurd-gear gear-spin-2"></div>
                </div>
                <div className="lego-slider">
                  <div className="slider-track-wrap">
                    <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
                    <div className="slider-track-groove">
                      <input
                        type="range"
                        className="vertical-slider"
                        min="1"
                        max="100"
                        value={sensValue}
                        onPointerDown={() => {
                          isDraggingRef.current.sens = true;
                          if (dragReleaseTimerRef.current.sens !== null) {
                            window.clearTimeout(dragReleaseTimerRef.current.sens);
                            dragReleaseTimerRef.current.sens = null;
                          }
                        }}
                        onPointerUp={() => {
                          dragReleaseTimerRef.current.sens = window.setTimeout(() => {
                            isDraggingRef.current.sens = false;
                            dragReleaseTimerRef.current.sens = null;
                          }, 400);
                        }}
                        onChange={e => {
                          const value = Number(e.target.value);
                          setSensValue(value);
                          isDraggingRef.current.sens = true;
                          sendThrottledSlider('set_sensibility', 'sens', value);
                        }}
                      />
                    </div>
                    <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* AUTO TRANSITION BLOCK */}
            <div style={{ position: 'absolute', top: '10px', left: '358px', width: '130px', height: '310px' }}>
              {/* Centered Label */}
              <div className="rogue-piece" style={{
                position: 'absolute', top: '0', left: '50%', transform: 'translateX(-50%)',
                width: '120px', height: '30px', backgroundColor: '#f4f4f4',
                borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
                display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '2px 5px 10px rgba(0,0,0,0.7)', borderRadius: '2px', zIndex: 5
              }}>
                <span style={{ color: '#000', fontWeight: '900', fontSize: '0.65rem', letterSpacing: '1px' }}>AUTO TRANS (S)</span>
              </div>
              {/* Slider Mechanism */}
              <div className="slider-container-group" style={{ position: 'absolute', top: '40px', right: '10px', width: '90px', '--slider-val': (autoTimeValue / 300) * 100 } as React.CSSProperties}>
                <div className="absurd-slider-mechanism">
                  <div className="technic-beam beam-1"></div>
                  <div className="technic-beam beam-2"></div>
                  <div className="guide-rail rail-1"></div>
                  <div className="guide-rail rail-3"></div>
                  <div className="rail-mount mount-1"></div>
                  <div className="rail-mount mount-2"></div>
                  <div className="rail-mount mount-3"></div>
                  <div className="absurd-weight weight-drop-1" style={{ backgroundColor: '#0055bf' }}></div>
                  <div className="absurd-gear gear-spin-1"></div>
                  <div className="absurd-gear gear-spin-2"></div>
                </div>
                <div className="lego-slider">
                  <div className="slider-track-wrap">
                    <div className="slider-scale">{[5, 30, 60, 90, 120, 150, 180, 210, 240, 300].map(n => <span key={n} style={{ fontSize: '0.4rem' }}>{n}</span>)}</div>
                    <div className="slider-track-groove">
                      <input
                        type="range"
                        className="vertical-slider"
                        min="5"
                        max="300"
                        value={autoTimeValue}
                        onPointerDown={() => {
                          isDraggingRef.current.autoTime = true;
                          if (dragReleaseTimerRef.current.autoTime !== null) {
                            window.clearTimeout(dragReleaseTimerRef.current.autoTime);
                            dragReleaseTimerRef.current.autoTime = null;
                          }
                        }}
                        onPointerUp={() => {
                          dragReleaseTimerRef.current.autoTime = window.setTimeout(() => {
                            isDraggingRef.current.autoTime = false;
                            dragReleaseTimerRef.current.autoTime = null;
                          }, 400);
                        }}
                        onChange={e => {
                          const value = Number(e.target.value);
                          setAutoTimeValue(value);
                          isDraggingRef.current.autoTime = true;
                          sendThrottledSlider('set_auto_transition_time', 'autoTime', value);
                        }}
                      />
                    </div>
                    <div className="slider-scale">{[5, 30, 60, 90, 120, 150, 180, 210, 240, 300].map(n => <span key={n} style={{ fontSize: '0.4rem' }}>{n}</span>)}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Thick Technic Cables connecting to the Config Board */}
          <div style={{ position: 'absolute', top: '160px', left: '-40px', width: '60px', height: '16px', backgroundColor: '#111', borderTop: '4px solid #333', borderBottom: '4px solid #000', borderRadius: '8px', boxShadow: '0 8px 10px rgba(0,0,0,0.8)', zIndex: -1, display: 'flex', alignItems: 'center' }}>
            <div style={{ width: '12px', height: '100%', backgroundColor: '#ffcd00', marginLeft: '15px' }}></div>
          </div>
          <div style={{ position: 'absolute', top: '220px', left: '-40px', width: '60px', height: '16px', backgroundColor: '#111', borderTop: '4px solid #333', borderBottom: '4px solid #000', borderRadius: '8px', boxShadow: '0 8px 10px rgba(0,0,0,0.8)', zIndex: -1, display: 'flex', alignItems: 'center' }}>
            <div style={{ width: '12px', height: '100%', backgroundColor: '#ffcd00', marginLeft: '15px' }}></div>
          </div>
          <div style={{ position: 'absolute', top: '280px', left: '-40px', width: '60px', height: '16px', backgroundColor: '#111', borderTop: '4px solid #333', borderBottom: '4px solid #000', borderRadius: '8px', boxShadow: '0 8px 10px rgba(0,0,0,0.8)', zIndex: -1, display: 'flex', alignItems: 'center' }}>
            <div style={{ width: '12px', height: '100%', backgroundColor: '#ffcd00', marginLeft: '15px' }}></div>
          </div>
        </div>
      </GridSpot>


      {/* ======================= CENTER COLUMN ======================= */}
      {/* Telemetry Bar (3 studs tall, 25 wide) */}
      <GridSpot col={17} row={0}>
        <div className="rogue-piece" style={{
          width: '900px', height: '90px',
          backgroundColor: '#1a1f24',
          borderTop: '8px solid #2a2d32', borderLeft: '8px solid #20252a', borderBottom: '8px solid #0a0a0a', borderRight: '8px solid #0f0f0f',
          boxSizing: 'border-box', position: 'relative', borderRadius: '4px',
          boxShadow: '5px 5px 15px rgba(0,0,0,0.8)'
        }}>
          <div className="stage-status-bar" style={{ width: '100%', height: '100%', margin: 0, border: 'none', background: 'transparent', boxShadow: 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 40px', boxSizing: 'border-box' }}>
            <div className="status-item">
              <span className="status-label" style={{ fontSize: '0.7rem' }}>CPU TEMP</span>
              <span className="status-value digital-font" style={{ fontSize: '1.4rem', color: 'var(--lego-orange)', textShadow: '0 0 5px var(--lego-orange)' }}>
                {formatTelemetryValue(systemTelemetry.cpuTempC, 'C', 1)}
              </span>
            </div>
            <div className="status-item" style={{ textAlign: 'center' }}>
              <span className="status-label" style={{ fontSize: '0.7rem' }}>MOOD</span>
              <span className="status-value" style={{ fontSize: '1.1rem', color: 'var(--lego-cyan)', fontWeight: 800, letterSpacing: '1px' }}>
                {currentMood || '--'}
              </span>
            </div>
            <div className="status-item" style={{ textAlign: 'center' }}>
              <span className="status-label" style={{ fontSize: '0.7rem' }}>DNA REGIME</span>
              <span className="status-value" style={{ fontSize: '1.1rem', color: 'var(--lego-purple)', fontWeight: 800, letterSpacing: '1px' }}>
                {currentConfiguration || '--'}
              </span>
            </div>
            <div className="status-item" style={{ textAlign: 'right' }}>
              <span className="status-label" style={{ fontSize: '0.7rem' }}>LATENCY</span>
              <span className="status-value digital-font" style={{ fontSize: '1.4rem', color: 'var(--lego-green)', textShadow: '0 0 5px var(--lego-green)' }}>
                {formatLatencyTelemetryValue(systemTelemetry.dynamicAudioLatencyMs)}
              </span>
            </div>
          </div>
          {/* Trans-Black Glass overlay */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 40%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.4) 100%)',
            boxShadow: 'inset 0 0 15px rgba(0,0,0,0.9)'
          }}></div>
        </div>
      </GridSpot>

      {/* Large Orange Baseplate Mount */}
      <GridSpot col={16} row={4} style={{ zIndex: 0 }}>
        <div className={`large-orange-baseplate ${isHold ? 'glow-red' : 'glow-green'}`} style={{ width: '960px', height: '420px' }}></div>
      </GridSpot>

      {/* Config Block */}
      <GridSpot col={18} row={6}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(23)}px`, height: `${LEGO_MATH.physicalSize(4)}px`, backgroundColor: '#a0a5a9',
          backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.5) 0%, rgba(0,0,0,0.1) 100%)',
          borderTop: '3px solid #dcdcdc', borderLeft: '3px solid #c8c8c8', borderBottom: '3px solid #646464', borderRight: '3px solid #787878',
          boxShadow: '5px 5px 15px rgba(0,0,0,0.6)', borderRadius: '2px',
          display: 'flex', alignItems: 'center', padding: '0 30px', justifyContent: 'flex-start', gap: '30px',
          position: 'relative', boxSizing: 'border-box'
        }}>
          {/* Physical Jumper Studs for greebling */}
          <div style={{ position: 'absolute', top: '10px', left: '10px', width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#a0a5a9', boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.6), inset -1px -1px 2px rgba(0,0,0,0.3), 1px 1px 3px rgba(0,0,0,0.4)' }}></div>
          <div style={{ position: 'absolute', bottom: '10px', right: '10px', width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#a0a5a9', boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.6), inset -1px -1px 2px rgba(0,0,0,0.3), 1px 1px 3px rgba(0,0,0,0.4)' }}></div>

          <div className="rogue-piece" style={{
            position: 'relative',
            backgroundColor: '#f4f4f4', padding: '8px 15px', borderRadius: '2px',
            borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
            boxShadow: '2px 2px 5px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <span style={{ color: '#000', fontWeight: '900', fontSize: '0.8rem', letterSpacing: '1px' }}>DNA REGIME</span>
          </div>
          <div style={{ position: 'relative', width: '240px', height: '40px' }}>
            <div className="rogue-piece" style={{
              position: 'absolute', inset: 0,
              backgroundColor: '#f4f4f4', pointerEvents: 'none',
              borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              padding: '0 15px', boxShadow: '2px 2px 5px rgba(0,0,0,0.4)', borderRadius: '2px'
            }}>
              <span style={{ color: '#000', fontWeight: '900', fontSize: '0.9rem', letterSpacing: '1px', pointerEvents: 'none' }}>
                {currentConfiguration || 'Live Random DNA'}
              </span>
            </div>
          </div>
        </div>
      </GridSpot>

      {/* Transition Block */}
      <GridSpot col={18} row={11}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(23)}px`, height: `${LEGO_MATH.physicalSize(4)}px`, backgroundColor: '#a0a5a9',
          backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.5) 0%, rgba(0,0,0,0.1) 100%)',
          borderTop: '3px solid #dcdcdc', borderLeft: '3px solid #c8c8c8', borderBottom: '3px solid #646464', borderRight: '3px solid #787878',
          boxShadow: '5px 5px 15px rgba(0,0,0,0.6)', borderRadius: '2px',
          display: 'flex', alignItems: 'center', padding: '0 30px', justifyContent: 'flex-start', gap: '30px',
          position: 'relative', boxSizing: 'border-box'
        }}>
          {/* Physical Jumper Studs */}
          <div style={{ position: 'absolute', top: '10px', left: '10px', width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#a0a5a9', boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.6), inset -1px -1px 2px rgba(0,0,0,0.3), 1px 1px 3px rgba(0,0,0,0.4)' }}></div>
          <div style={{ position: 'absolute', bottom: '10px', right: '10px', width: '16px', height: '16px', borderRadius: '50%', backgroundColor: '#a0a5a9', boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.6), inset -1px -1px 2px rgba(0,0,0,0.3), 1px 1px 3px rgba(0,0,0,0.4)' }}></div>

          <div className="rogue-piece" style={{
            position: 'relative',
            backgroundColor: '#f4f4f4', padding: '8px 15px', borderRadius: '2px',
            borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
            boxShadow: '2px 2px 5px rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <span style={{ color: '#000', fontWeight: '900', fontSize: '0.8rem', letterSpacing: '1px' }}>NEXT TRANSITION</span>
          </div>

          <div style={{ position: 'relative', width: '150px', height: '40px' }}>
            <div className="rogue-piece" style={{
              position: 'absolute', inset: 0,
              backgroundColor: '#f4f4f4', pointerEvents: 'none',
              borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '0 15px', boxShadow: '2px 2px 5px rgba(0,0,0,0.4)', borderRadius: '2px'
            }}>
              <span style={{ color: '#000', fontWeight: '900', fontSize: '0.9rem', letterSpacing: '1px', pointerEvents: 'none' }}></span>
              <span style={{ color: '#000', fontSize: '0.7rem', pointerEvents: 'none' }}>▼</span>
            </div>
            <select className="lego-select-transparent" style={{
              width: '100%', height: '100%', background: 'transparent', color: '#000', border: 'none',
              padding: '0 15px', fontSize: '0.9rem', outline: 'none', cursor: 'pointer', fontFamily: 'inherit', fontWeight: '900',
              appearance: 'none', position: 'relative', zIndex: 2
            }}
            value={selectedTransition}
            onChange={(e) => {
              const transition = e.target.value;
              setSelectedTransition(transition);
              sendInstruction({ page: 'live_deck', action: 'select_transition', payload: { transition } });
            }}>
              {transitions.map((transition) => (
                <option key={transition}>{transition}</option>
              ))}
            </select>
          </div>
          {/* Square 2x2 Plate Button */}
          <button className="rogue-piece rect-action-button" style={{
            position: 'relative',
            width: '80px', height: '80px', margin: 0, padding: 0, borderRadius: '6px', border: 'none',
            backgroundColor: '#0055bf', cursor: 'pointer',
            boxShadow: 'inset 2px 2px 6px rgba(255,255,255,0.5), inset -4px -4px 10px rgba(0,0,0,0.6), 5px 5px 15px rgba(0,0,0,0.8), 0 0 25px rgba(0, 85, 191, 0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            opacity: 1,
            overflow: 'visible'
          }}
          onClick={() => sendInstruction({
            page: 'live_deck',
            action: 'go_to_next_configuration',
            payload: { transition: selectedTransition }
          })}>
            {/* Square Glowing Ring */}
            <div style={{
              position: 'absolute',
              inset: '-8px',
              borderRadius: '10px',
              border: '2px solid rgba(0, 181, 226, 0.4)',
              boxShadow: '0 0 20px rgba(0, 181, 226, 0.5), inset 0 0 10px rgba(0, 181, 226, 0.3)',
              pointerEvents: 'none',
              animation: 'pulse-ring 2s infinite'
            }} />
            
            <div style={{
              width: '100%',
              height: '100%',
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gridTemplateRows: '1fr 1fr',
              placeItems: 'center',
              position: 'relative',
              zIndex: 2,
              padding: '10px',
              boxSizing: 'border-box'
            }}>
              {/* 4 Studs in a square pattern */}
              <div className="stud stud-blue" style={{ width: '20px', height: '20px', backgroundColor: '#00b5e2', boxShadow: 'inset 2px 2px 4px rgba(255,255,255,0.8), 0 0 8px rgba(0,181,226,0.6)' }}></div>
              <div className="stud stud-blue" style={{ width: '20px', height: '20px', backgroundColor: '#00b5e2', boxShadow: 'inset 2px 2px 4px rgba(255,255,255,0.8), 0 0 8px rgba(0,181,226,0.6)' }}></div>
              <div className="stud stud-blue" style={{ width: '20px', height: '20px', backgroundColor: '#00b5e2', boxShadow: 'inset 2px 2px 4px rgba(255,255,255,0.8), 0 0 8px rgba(0,181,226,0.6)' }}></div>
              <div className="stud stud-blue" style={{ width: '20px', height: '20px', backgroundColor: '#00b5e2', boxShadow: 'inset 2px 2px 4px rgba(255,255,255,0.8), 0 0 8px rgba(0,181,226,0.6)' }}></div>
              
              {/* Centered GO text overlay */}
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                color: 'white',
                fontWeight: '900',
                fontSize: '1.2rem',
                textShadow: '0 0 10px rgba(0, 255, 255, 0.8), 0 2px 4px rgba(0,0,0,0.9)',
                letterSpacing: '2px',
                pointerEvents: 'none',
                zIndex: 3
              }}>GO</div>
            </div>
          </button>
        </div>
      </GridSpot>

      {/* Lock Trans Switch */}
      <GridSpot col={42} row={6}>
        <label className="lock-switch-container">
          <input
            type="checkbox"
            className="heavy-duty-checkbox"
            checked={isHold}
            onChange={(e) => {
              const locked = e.target.checked;
              setIsHold(locked);
              sendInstruction({ page: 'live_deck', action: 'lock_current_configuration', payload: { locked } });
            }}
          />

          <div className="lock-status-display">
            <span className="lock-text lock-text-hold">HOLD</span>
            <span className="lock-text lock-text-live">LIVE</span>
          </div>

          <div className="heavy-duty-track">

            <div className="mech-system">
              <div className="mech-gear gear-left"></div>
              <div className="mech-gear gear-right"></div>
              <div className="mech-weight weight-left"></div>
              <div className="mech-weight weight-right"></div>
              <div className="mech-piston"></div>
              <div className="mech-bolt bolt-left"></div>
              <div className="mech-bolt bolt-right"></div>
            </div>

            <div className="heavy-duty-brick">
              <div className="round-stud-grid-2x2">
                <div className="stud stud-red"></div>
                <div className="stud stud-red"></div>
                <div className="stud stud-red"></div>
                <div className="stud stud-red"></div>
              </div>
            </div>
          </div>
        </label>
      </GridSpot>

      {/* Drop Button */}
      <GridSpot col={17} row={21}>
        <div
          className="drop-button-container"
          style={{
            width: `${DROP_BUTTON_WIDTH_PX - DROP_BUTTON_CROP_PX}px`,
            height: `${DROP_BUTTON_HEIGHT_PX - DROP_BUTTON_CROP_PX}px`,
            marginTop: 'calc(0.35 * var(--stud))',
          }}
        >
          <button
            type="button"
            className="giant-drop-button"
            aria-label="Manual drop"
            style={{
              width: `${DROP_BUTTON_WIDTH_PX}px`,
              height: `${DROP_BUTTON_HEIGHT_PX}px`,
            }}
            onClick={() => sendInstruction({ page: 'live_deck', action: 'manual_drop' })}
          >
            <div
              className="drop-button-letterfield"
              style={{
                gridTemplateColumns: `repeat(${DROP_STUD_COLS}, var(--stud))`,
                gridTemplateRows: `repeat(${DROP_STUD_ROWS}, var(--stud))`,
              }}
              aria-hidden
            >
              {DROP_TILE_PLACEMENTS.map((tile, index) => (
                <div
                  key={index}
                  className={`flat-1x1-tile flat-1x1-tile--${tile.variant}`}
                  style={{
                    gridColumn: tile.col + DROP_LETTER_START_COL + 1,
                    gridRow: tile.row + DROP_LETTER_START_ROW + 1,
                    transform: `rotate(${tile.rotationDeg}deg)`,
                  }}
                />
              ))}
            </div>
          </button>
        </div>
      </GridSpot>


      {/* ======================= LEFT MOOD PALETTES COLUMN ======================= */}
      <GridSpot col={0} row={0}>
        <div className="rogue-piece" style={{
          width: '360px', height: '45px',
          backgroundColor: '#fcd000',
          backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)',
          borderTop: '2px solid rgba(255,255,255,0.6)', borderLeft: '2px solid rgba(255,255,255,0.3)', borderBottom: '2px solid rgba(0,0,0,0.4)', borderRight: '2px solid rgba(0,0,0,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '2px 2px 5px rgba(0,0,0,0.5)', borderRadius: '2px', position: 'relative'
        }}>
          <div style={{ backgroundColor: '#fcd000', padding: '0 15px', border: '1px solid #000', boxShadow: '0 0 0 1px #fcd000' }}>
            <span style={{ color: '#000', fontWeight: '900', fontSize: '0.85rem', letterSpacing: '1px', textTransform: 'uppercase' }}>Mood Palettes</span>
          </div>
        </div>
      </GridSpot>

      {MOOD_PALETTES.map((mood, i) => {
        const isActive = currentMood.toLowerCase() === mood.name.toLowerCase();
        return (
          <GridSpot key={mood.name} col={0} row={2 + i * 4}>
            <button
              className={`preset-brick ${mood.colorClass}`}
              style={{
                width: '360px',
                height: '84px',
                position: 'relative',
                boxShadow: isActive
                  ? `0 0 20px ${mood.accent}, inset 0 0 12px rgba(255,255,255,0.6)`
                  : undefined,
                border: isActive ? `2px solid ${mood.accent}` : '1px solid rgba(0, 0, 0, 0.8)',
              }}
              onClick={() => {
                setCurrentMood(mood.name);
                sendInstruction({ page: 'live_deck', action: 'select_mood', payload: { palette: mood.name } });
              }}
            >
              {/* Printed White Tile Label */}
              <div className="rogue-piece" style={{
                position: 'absolute', top: '50%', left: '15px', transform: 'translateY(-50%)',
                width: '230px', height: '27px', backgroundColor: '#f4f4f4',
                borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '2px 2px 5px rgba(0,0,0,0.6)', borderRadius: '2px'
              }}>
                <span style={{ color: '#000', fontWeight: 'bold', fontSize: '0.9rem', letterSpacing: '0.5px' }}>{mood.name}</span>
              </div>
              {/* Round 1x1 Stud Indicator */}
              <div className="rogue-piece" style={{
                position: 'absolute', right: '15px', top: '50%', transform: 'translateY(-50%)',
                width: 'var(--stud-diameter)', height: 'var(--stud-diameter)', borderRadius: '50%',
                backgroundColor: isActive ? mood.accent : '#fcd000',
                boxShadow: isActive
                  ? `0 0 10px ${mood.accent}, inset 1px 1px 2px rgba(255,255,255,0.8)`
                  : 'inset 1px 1px 2px rgba(255,255,255,0.8), inset -1px -1px 2px rgba(0,0,0,0.3), 2px 2px 4px rgba(0,0,0,0.6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <span style={{ color: '#000', fontWeight: 'bold', fontSize: '0.85rem' }}>{i + 1}</span>
              </div>
            </button>
          </GridSpot>
        );
      })}

      </div>
    </FitBoard>
  );
};
