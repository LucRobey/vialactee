import React, { useEffect, useState } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { wideDropStudPattern } from '../../constants/dropPatterns';
import { sendInstruction, subscribeModeMasterState } from '../../utils/controlBridge';

export const LiveDeck = () => {
  const [lumValue, setLumValue] = useState(60);
  const [sensValue, setSensValue] = useState(70);
  const [isHold, setIsHold] = useState(false);
  const [selectedConfiguration, setSelectedConfiguration] = useState('TECHNO 1');
  const [selectedTransition, setSelectedTransition] = useState('CUT');
  const [currentPlaylist, setCurrentPlaylist] = useState('TECHNO 1');
  const [currentConfiguration, setCurrentConfiguration] = useState('TECHNO 1');
  const [availablePlaylists, setAvailablePlaylists] = useState(['TECHNO 1', 'HOUSE 2', 'LOFI', 'DNB', 'DISCO', 'BASS', 'TRAP', 'AMBIENT']);
  const [availableConfigurations, setAvailableConfigurations] = useState(['TECHNO 1', 'HOUSE 2', 'LOFI', 'DNB']);

  const transitions = ['CUT', 'FADE IN/OUT', 'CROSSFADE'];
  const presetColors = ['bg-blue', 'bg-orange', 'bg-green', 'bg-purple', 'bg-yellow', 'bg-red', 'bg-cyan', 'bg-magenta'];

  useEffect(() => {
    return subscribeModeMasterState((state) => {
      setLumValue(state.luminosity);
      setSensValue(state.sensibility);
      setIsHold(state.transitionLocked);
      setSelectedTransition(state.selectedTransition);

      if (state.activePlaylist) {
        setCurrentPlaylist(state.activePlaylist);
      }
      const activeConfiguration = state.activeConfiguration;
      if (activeConfiguration) {
        setCurrentConfiguration(activeConfiguration);
        setAvailableConfigurations(prev => prev.includes(activeConfiguration) ? prev : [...prev, activeConfiguration]);
      }
      const queuedConfiguration = state.queuedConfiguration;
      if (queuedConfiguration) {
        setSelectedConfiguration(queuedConfiguration);
        setAvailableConfigurations(prev => prev.includes(queuedConfiguration) ? prev : [...prev, queuedConfiguration]);
      }
      if (state.playlists.length > 0) {
        setAvailablePlaylists(state.playlists);
      }
    });
  }, []);

  return (
    <div className="live-deck-grid">

      {/* ======================= LEFT COLUMN ======================= */}
      <GridSpot col={0} row={0}>
        <div style={{
          width: `${LEGO_MATH.physicalSize(6)}px`,
          height: `${LEGO_MATH.physicalSize(26)}px`,
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
          {/* Deep dark pit spanning the height of the sliders */}
          <div style={{
            position: 'absolute',
            top: '15px', bottom: '15px', left: '15px', right: '15px',
            backgroundColor: '#0a0d12',
            borderRadius: '4px',
            boxShadow: 'inset 10px 10px 20px rgba(0,0,0,0.95), inset -5px -5px 15px rgba(0,0,0,0.8), 0 2px 2px rgba(255,255,255,0.1)'
          }}>
            {/* LUMINOSITÉ BLOCK */}
            <div style={{ position: 'absolute', top: '10px', left: '2px', right: '0', height: '310px' }}>
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
                        onChange={e => {
                          const value = Number(e.target.value);
                          setLumValue(value);
                          sendInstruction({ page: 'live_deck', action: 'set_luminosity', payload: { value } });
                        }}
                      />
                    </div>
                    <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* SENSIBILITÉ BLOCK */}
            <div style={{ position: 'absolute', top: '375px', left: '2px', right: '0', height: '310px' }}>
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
                        onChange={e => {
                          const value = Number(e.target.value);
                          setSensValue(value);
                          sendInstruction({ page: 'live_deck', action: 'set_sensibility', payload: { value } });
                        }}
                      />
                    </div>
                    <div className="slider-scale">{[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(n => <span key={n}>{n}</span>)}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Thick Technic Cables connecting to the Config Board */}
          <div style={{ position: 'absolute', top: '160px', right: '-40px', width: '60px', height: '16px', backgroundColor: '#111', borderTop: '4px solid #333', borderBottom: '4px solid #000', borderRadius: '8px', boxShadow: '0 8px 10px rgba(0,0,0,0.8)', zIndex: -1, display: 'flex', alignItems: 'center' }}>
            <div style={{ width: '12px', height: '100%', backgroundColor: '#ffcd00', marginLeft: '15px' }}></div>
          </div>
          <div style={{ position: 'absolute', top: '500px', right: '-40px', width: '60px', height: '16px', backgroundColor: '#111', borderTop: '4px solid #333', borderBottom: '4px solid #000', borderRadius: '8px', boxShadow: '0 8px 10px rgba(0,0,0,0.8)', zIndex: -1, display: 'flex', alignItems: 'center' }}>
            <div style={{ width: '12px', height: '100%', backgroundColor: '#ffcd00', marginLeft: '15px' }}></div>
          </div>
        </div>
      </GridSpot>


      {/* ======================= CENTER COLUMN ======================= */}
      {/* Telemetry Bar (3 studs tall, 25 wide) */}
      <GridSpot col={8} row={0}>
        <div className="rogue-piece" style={{
          width: '750px', height: '90px',
          backgroundColor: '#1a1f24',
          borderTop: '8px solid #2a2d32', borderLeft: '8px solid #20252a', borderBottom: '8px solid #0a0a0a', borderRight: '8px solid #0f0f0f',
          boxSizing: 'border-box', position: 'relative', borderRadius: '4px',
          boxShadow: '5px 5px 15px rgba(0,0,0,0.8)'
        }}>
          <div className="stage-status-bar" style={{ width: '100%', height: '100%', margin: 0, border: 'none', background: 'transparent', boxShadow: 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 40px', boxSizing: 'border-box' }}>
            <div className="status-item">
              <span className="status-label" style={{ fontSize: '0.7rem' }}>CPU</span>
              <span className="status-value digital-font" style={{ fontSize: '1.4rem', color: 'var(--lego-orange)', textShadow: '0 0 5px var(--lego-orange)' }}>42%</span>
            </div>
            <div className="status-item" style={{ textAlign: 'center' }}>
              <span className="status-label" style={{ fontSize: '0.7rem' }}>PLAYLIST</span>
              <span className="status-value" style={{ fontSize: '1.1rem', color: 'var(--lego-cyan)', fontWeight: 800, letterSpacing: '1px' }}>{currentPlaylist}</span>
            </div>
            <div className="status-item" style={{ textAlign: 'center' }}>
              <span className="status-label" style={{ fontSize: '0.7rem' }}>CONFIG</span>
              <span className="status-value" style={{ fontSize: '1.1rem', color: 'var(--lego-purple)', fontWeight: 800, letterSpacing: '1px' }}>{currentConfiguration}</span>
            </div>
            <div className="status-item" style={{ textAlign: 'right' }}>
              <span className="status-label" style={{ fontSize: '0.7rem' }}>LATENCY</span>
              <span className="status-value digital-font" style={{ fontSize: '1.4rem', color: 'var(--lego-green)', textShadow: '0 0 5px var(--lego-green)' }}>12ms</span>
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
      <GridSpot col={7} row={4} style={{ zIndex: 0 }}>
        <div className={`large-orange-baseplate ${isHold ? 'glow-red' : 'glow-green'}`} style={{ width: '810px', height: '330px' }}></div>
      </GridSpot>

      {/* Config Block */}
      <GridSpot col={8} row={5}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(19)}px`, height: `${LEGO_MATH.physicalSize(4)}px`, backgroundColor: '#a0a5a9',
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
            <span style={{ color: '#000', fontWeight: '900', fontSize: '0.8rem', letterSpacing: '1px' }}>NEXT CONFIGURATION</span>
          </div>
          {/* Working Dropdown inside a fake printed tile wrapper */}
          <div style={{ position: 'relative', width: '240px', height: '40px' }}>
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
            value={selectedConfiguration}
            onChange={(e) => {
              const configuration = e.target.value;
              setSelectedConfiguration(configuration);
              sendInstruction({ page: 'live_deck', action: 'select_configuration', payload: { configuration } });
            }}>
              {availableConfigurations.map((config) => (
                <option key={config}>{config}</option>
              ))}
            </select>
          </div>
        </div>
      </GridSpot>

      {/* Transition Block */}
      <GridSpot col={8} row={10}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(19)}px`, height: `${LEGO_MATH.physicalSize(4)}px`, backgroundColor: '#a0a5a9',
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
          {/* Round 2x2 Plate Button */}
          <button className="rogue-piece" style={{
            position: 'relative',
            width: '64px', height: '64px', margin: 0, padding: 0, borderRadius: '50%', border: 'none',
            backgroundColor: '#0055bf', cursor: 'pointer',
            boxShadow: 'inset 2px 2px 5px rgba(255,255,255,0.4), inset -3px -3px 8px rgba(0,0,0,0.6), 4px 4px 10px rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}
          onClick={() => sendInstruction({
            page: 'live_deck',
            action: 'go_to_next_configuration',
            payload: { configuration: selectedConfiguration, transition: selectedTransition }
          })}>
            <div className="round-stud-grid" style={{ transform: 'scale(0.85)', margin: 0 }}>
              <div className="stud stud-blue"></div>
              <div className="stud stud-blue"></div>
              <div className="stud stud-blue"></div>
              <div className="stud stud-blue"></div>
            </div>
          </button>
        </div>
      </GridSpot>

      {/* Lock Trans Switch */}
      <GridSpot col={28} row={5}>
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
      <GridSpot col={8} row={16}>
        <div className="drop-button-container" style={{ width: '750px' }}>
          <button
            className="giant-drop-button"
            style={{ width: '100%' }}
            onClick={() => sendInstruction({ page: 'live_deck', action: 'manual_drop' })}
          >
            <div className="drop-stud-grid">
              {(() => {
                let whiteIndex = 0;
                return wideDropStudPattern.flat().map((isWhite, i) => {
                  if (!isWhite) return <div key={i} className="stud stud-red"></div>;

                  const currentIndex = whiteIndex++;
                  // Generate a pseudo-random rotation and shape
                  const rotation = ((i * 17) % 15) - 7;
                  const isSquare = (i * 13) % 2 === 0;

                  // Assign colors to specific indices (2 yellow, 1 grey, 5 clears)
                  const isYellow = currentIndex === 8 || currentIndex === 24;
                  const isGrey = currentIndex === 16;
                  const isClear = [4, 11, 18, 27, 34].includes(currentIndex);

                  let colorClass = '';
                  if (isYellow) colorClass = 'piece-yellow';
                  else if (isGrey) colorClass = 'piece-grey';

                  return (
                    <div
                      key={i}
                      className={`stud-piece ${isSquare ? 'piece-square' : 'piece-circle'} ${colorClass} ${isClear ? 'piece-clear' : ''}`}
                      style={{ transform: `rotate(${rotation}deg)` }}
                    ></div>
                  );
                });
              })()}
            </div>
          </button>
        </div>
      </GridSpot>


      {/* ======================= RIGHT COLUMN ======================= */}
      <GridSpot col={35} row={0}>
        <div className="rogue-piece" style={{
          width: '240px', height: 'calc(1 * var(--stud))',
          backgroundColor: '#fcd000',
          backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)',
          borderTop: '2px solid rgba(255,255,255,0.6)', borderLeft: '2px solid rgba(255,255,255,0.3)', borderBottom: '2px solid rgba(0,0,0,0.4)', borderRight: '2px solid rgba(0,0,0,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '2px 2px 5px rgba(0,0,0,0.5)', borderRadius: '2px', position: 'relative'
        }}>
          <div style={{ backgroundColor: '#fcd000', padding: '0 15px', border: '1px solid #000', boxShadow: '0 0 0 1px #fcd000' }}>
            <span style={{ color: '#000', fontWeight: '900', fontSize: '0.65rem', letterSpacing: '1px', textTransform: 'uppercase' }}>Presets</span>
          </div>
        </div>
      </GridSpot>

      {availablePlaylists.slice(0, 8).map((name, i) => (
        <GridSpot key={name} col={35} row={2 + i * 3}>
          <button
            className={`preset-brick ${presetColors[i % presetColors.length]}`}
            style={{ width: '240px', position: 'relative' }}
            onClick={() => {
              setCurrentPlaylist(name);
              sendInstruction({ page: 'live_deck', action: 'select_playlist', payload: { playlist: name } });
            }}
          >
            {/* Printed White Tile Label */}
            <div className="rogue-piece" style={{
              position: 'absolute', top: '50%', left: '15px', transform: 'translateY(-50%)',
              width: '120px', height: '18px', backgroundColor: '#f4f4f4',
              borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '2px 2px 5px rgba(0,0,0,0.6)', borderRadius: '2px'
            }}>
              <span style={{ color: '#000', fontWeight: 'bold', fontSize: '0.6rem', letterSpacing: '0.5px' }}>{name}</span>
            </div>
            {/* Round 1x1 Stud Indicator */}
            <div className="rogue-piece" style={{
              position: 'absolute', right: '15px', top: '50%', transform: 'translateY(-50%)',
              width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#fcd000',
              boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.8), inset -1px -1px 2px rgba(0,0,0,0.3), 2px 2px 4px rgba(0,0,0,0.6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <span style={{ color: '#000', fontWeight: 'bold', fontSize: '0.65rem' }}>{i + 1}</span>
            </div>
          </button>
        </GridSpot>
      ))}
      <GridSpot col={35} row={26}>
        <button
          className="preset-brick bg-dark-blue"
          style={{ width: '240px', position: 'relative' }}
          onClick={() => {
            setCurrentPlaylist('CUSTOM');
            sendInstruction({ page: 'live_deck', action: 'select_playlist', payload: { playlist: 'CUSTOM' } });
          }}
        >
          <div className="rogue-piece" style={{
            position: 'absolute', top: '50%', left: '15px', transform: 'translateY(-50%)',
            width: '120px', height: '18px', backgroundColor: '#f4f4f4',
            borderTop: '2px solid #fff', borderLeft: '2px solid #ddd', borderBottom: '2px solid #999', borderRight: '2px solid #ccc',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '2px 2px 5px rgba(0,0,0,0.6)', borderRadius: '2px'
          }}>
            <span style={{ color: '#000', fontWeight: 'bold', fontSize: '0.6rem', letterSpacing: '0.5px' }}>CUSTOM</span>
          </div>
          <div className="rogue-piece" style={{
            position: 'absolute', right: '15px', top: '50%', transform: 'translateY(-50%)',
            width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#fcd000',
            boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.8), inset -1px -1px 2px rgba(0,0,0,0.3), 2px 2px 4px rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <span style={{ color: '#000', fontWeight: 'bold', fontSize: '0.65rem' }}>9</span>
          </div>
        </button>
      </GridSpot>

    </div>
  );
};
