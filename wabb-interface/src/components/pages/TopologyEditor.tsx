import React, { useCallback, useState, useEffect } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { AVAILABLE_MODES } from '../../constants/modes';
import { initialTopology, MAP_OFFSET_C, MAP_OFFSET_R, INSPECTOR_OFFSET_C, INSPECTOR_OFFSET_R } from '../../constants/topologyData';
import { sendInstruction, subscribeModeMasterState, type ModeMasterState } from '../../utils/controlBridge';

export type EditorMode = 'LIVE' | 'MODIFY' | 'BUILD';

// SVG Cable helper
const Cable = ({ start, end, cp1, cp2 }: { start: number[], end: number[], cp1: number[], cp2: number[] }) => {
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
      {/* Glossy highlight line on the thick cable */}
      <path d={`M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${ex} ${ey}`} stroke="rgba(255,255,255,0.15)" strokeWidth="3" fill="none" strokeLinecap="round" transform="translate(-2, -2)" />

      {/* Start Plug (Segment side) */}
      <circle cx={sx} cy={sy} r={14} fill="#2a2d32" stroke="#111" strokeWidth="2" filter="url(#drop-shadow-wire)" />
      <circle cx={sx} cy={sy} r={8} fill="#1a1f24" />
      <circle cx={sx} cy={sy} r={4} fill="#0a0a0a" />

      {/* End Plug (Console side) */}
      <circle cx={ex} cy={ey} r={14} fill="#2a2d32" stroke="#111" strokeWidth="2" filter="url(#drop-shadow-wire)" />
      <circle cx={ex} cy={ey} r={8} fill="#1a1f24" />
      <circle cx={ex} cy={ey} r={4} fill="#0a0a0a" />
    </>
  );
};

export const TopologyEditor = () => {
  const [segments, setSegments] = useState(initialTopology);
  const [selectedSegId, setSelectedSegId] = useState(initialTopology[0].id);
  const [editorMode, setEditorMode] = useState<EditorMode>('LIVE');
  const [configName, setConfigName] = useState('');
  
  // Real API state
  const [apiPlaylists, setApiPlaylists] = useState<string[]>(['PLAYLIST_A']);
  const [apiConfigurations, setApiConfigurations] = useState<Record<string, any[]>>({});
  
  const [playlistIndex, setPlaylistIndex] = useState(0);
  const playlist = apiPlaylists[playlistIndex] || 'PLAYLIST_A';

  const applyModeMasterState = useCallback((state: ModeMasterState) => {
    if (state.playlists.length > 0) {
      setApiPlaylists(state.playlists);
    }

    if (state.activePlaylist) {
      const playlists = state.playlists.length > 0 ? state.playlists : apiPlaylists;
      const nextPlaylistIndex = playlists.findIndex(name => name === state.activePlaylist);
      if (nextPlaylistIndex >= 0) {
        setPlaylistIndex(nextPlaylistIndex);
      }
    }

    if (state.activeConfiguration) {
      setConfigName(state.activeConfiguration);
    }

    if (editorMode === 'LIVE') {
      setSegments(prev => prev.map(seg => {
        const liveSegment = state.segments.find(remote => remote.id === seg.id);
        if (!liveSegment) {
          return seg;
        }
        return {
          ...seg,
          mode: liveSegment.mode,
          direction: liveSegment.direction,
        };
      }));
    }
  }, [apiPlaylists, editorMode]);

  useEffect(() => {
    fetch('/api/configurations')
      .then(res => res.json())
      .then(data => {
        if(data.playlists && data.playlists.length > 0) {
          setApiPlaylists(data.playlists);
        }
        if(data.configurations) {
          setApiConfigurations(data.configurations);
        }
      })
      .catch(err => console.error("Could not load configurations", err));
  }, []);

  useEffect(() => {
    return subscribeModeMasterState(applyModeMasterState);
  }, [applyModeMasterState]);

  const handlePlaylistCycle = (dir: 1 | -1) => {
    setPlaylistIndex(prev => {
      let next = prev + dir;
      if (next >= apiPlaylists.length) next = 0;
      if (next < 0) next = apiPlaylists.length - 1;
      const selectedPlaylist = apiPlaylists[next] || 'PLAYLIST_A';
      sendInstruction({
        page: 'topology',
        action: 'select_playlist_slot',
        payload: { playlist: selectedPlaylist, direction: dir === 1 ? 'next' : 'previous' }
      });
      return next;
    });
  };

  const handleConfigSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedName = e.target.value;
    setConfigName(selectedName);
    sendInstruction({
      page: 'topology',
      action: 'select_configuration',
      payload: { playlist, configuration: selectedName }
    });
    const configsForPlaylist = apiConfigurations[playlist] || [];
    const selectedConfig = configsForPlaylist.find((c: any) => c.name === selectedName);
    if (selectedConfig) {
      // Map it back to segments
      setSegments(prev => prev.map(seg => {
        const key = `Segment ${seg.id}`;
        const mode = selectedConfig.modes[key] || seg.mode;
        const direction = selectedConfig.way ? (selectedConfig.way[key] || (seg as any).direction || 'UP') : ((seg as any).direction || 'UP');
        return { ...seg, mode, direction };
      }));
    }
  };

  const handleSave = () => {
    if (!configName) return alert("Please enter a configuration name.");

    const newModes: Record<string, string> = {};
    const newWay: Record<string, string> = {};
    segments.forEach(seg => {
      const key = `Segment ${seg.id}`;
      newModes[key] = seg.mode;
      newWay[key] = (seg as any).direction || 'UP';
    });

    const newConfig = {
      name: configName,
      modes: newModes,
      way: newWay
    };

    const updatedConfigs = { ...apiConfigurations };
    if (!updatedConfigs[playlist]) updatedConfigs[playlist] = [];

    if (editorMode === 'MODIFY') {
      const idx = updatedConfigs[playlist].findIndex((c:any) => c.name === configName);
      if (idx !== -1) {
        updatedConfigs[playlist][idx] = newConfig;
      } else {
        updatedConfigs[playlist].push(newConfig);
      }
    } else {
      updatedConfigs[playlist].push(newConfig);
    }

    const payload = {
      playlists: apiPlaylists,
      configurations: updatedConfigs
    };

    fetch('/api/configurations', {
      method: 'POST',
      body: JSON.stringify(payload)
    }).then(() => {
      setApiConfigurations(updatedConfigs);
      sendInstruction({
        page: 'topology',
        action: editorMode === 'BUILD' ? 'build_configuration' : 'modify_configuration',
        payload: { playlist, configuration: configName }
      });
      alert(`Configuration ${configName} saved successfully to ${playlist}!`);
    }).catch(err => console.error(err));
  };

  const selectedSeg = segments.find(s => s.id === selectedSegId)!;

  const handleModeSelect = (modeName: string) => {
    sendInstruction({
      page: 'topology',
      action: 'select_segment_mode',
      payload: { segmentId: selectedSegId, mode: modeName }
    });
    setSegments(prev => prev.map(seg => seg.id === selectedSegId ? { ...seg, mode: modeName } : seg));
  };

  const handleDirectionToggle = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSegments(prev => prev.map(seg => {
      if (seg.id !== id) return seg;
      const direction = (seg as any).direction === 'UP' ? 'DOWN' : 'UP';
      sendInstruction({
        page: 'topology',
        action: 'toggle_segment_direction',
        payload: { segmentId: id, direction }
      });
      return { ...seg, direction };
    }));
  };

  const getModeClass = (modeName: string) => `anim-${modeName.toLowerCase().replace(/\s+/g, '-')}`;

  // Calculate junction boxes where segments intersect (a simple AABB collision check on the grid)
  const junctions: { col: number, row: number }[] = [];
  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      const s1 = segments[i];
      const s2 = segments[j];
      const r1 = { left: s1.col, right: s1.col + (s1.orientation === 'horizontal' ? s1.w : 2), top: s1.row, bottom: s1.row + (s1.orientation === 'vertical' ? s1.h : 2) };
      const r2 = { left: s2.col, right: s2.col + (s2.orientation === 'horizontal' ? s2.w : 2), top: s2.row, bottom: s2.row + (s2.orientation === 'vertical' ? s2.h : 2) };

      if (r1.left < r2.right && r1.right > r2.left && r1.top < r2.bottom && r1.bottom > r2.top) {
        // Find top-left of intersection
        const ix = Math.max(r1.left, r2.left);
        const iy = Math.max(r1.top, r2.top);
        junctions.push({ col: ix, row: iy });
      }
    }
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(35 * var(--stud))' }}>

      {/* Map Background Baseplate */}
      <GridSpot col={MAP_OFFSET_C - 1} row={MAP_OFFSET_R - 3} style={{ zIndex: 0 }}>
        <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(47)}px`, height: `${LEGO_MATH.physicalSize(29)}px`, boxShadow: 'inset 0 0 40px #000' }}></div>
      </GridSpot>

      {/* 3-Way Mode Master Switch - Dark Green Baseplate */}
      <GridSpot col={INSPECTOR_OFFSET_C + 31} row={INSPECTOR_OFFSET_R + 5} style={{ zIndex: 10 }}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(7)}px`,
          height: `${LEGO_MATH.physicalSize(6)}px`,
          backgroundColor: '#1b4a22', // Dark green
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
          boxShadow: '6px 6px 15px rgba(0,0,0,0.8)'
        }}></div>
      </GridSpot>

      {/* Pins for Dark Green Baseplate */}
      {[{ c: 10, r: -12 }, { c: 16, r: -12 }, { c: 10, r: -7 }, { c: 16, r: -7 }].map((pos, i) => (
        <GridSpot key={`green-pin-${i}`} col={INSPECTOR_OFFSET_C + 21 + pos.c} row={INSPECTOR_OFFSET_R + 17 + pos.r} style={{ zIndex: 11 }}>
          <div style={{ width: '30px', height: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{
              width: '18px', height: '18px', borderRadius: '50%',
              backgroundColor: '#1a1a1a',
              boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.3), inset -2px -2px 4px rgba(0,0,0,0.8), 2px 2px 3px rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <div style={{ position: 'relative', width: '10px', height: '10px' }}>
                <div style={{ position: 'absolute', top: '3.5px', left: '0px', width: '10px', height: '3px', backgroundColor: '#050505', boxShadow: 'inset 1px 1px 1px rgba(0,0,0,1)' }}></div>
                <div style={{ position: 'absolute', top: '0px', left: '3.5px', width: '3px', height: '10px', backgroundColor: '#050505', boxShadow: 'inset 1px 1px 1px rgba(0,0,0,1)' }}></div>
              </div>
            </div>
          </div>
        </GridSpot>
      ))}

      {/* Inset Screen Area for Switch */}
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
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'space-evenly', padding: '5px 0'
        }}>
          {(['LIVE', 'MODIFY', 'BUILD'] as const).map(mode => (
            <div key={mode}
              onClick={() => {
                setEditorMode(mode);
                sendInstruction({ page: 'topology', action: 'set_editor_mode', payload: { mode } });
              }}
              style={{
                width: '85%', textAlign: 'center', padding: '6px 0',
                backgroundColor: editorMode === mode ? (mode === 'LIVE' ? '#28a745' : mode === 'BUILD' ? '#d22020' : '#fcd000') : '#111',
                color: editorMode === mode ? '#000' : '#888',
                fontWeight: '900', fontSize: '0.65rem',
                cursor: 'pointer', borderRadius: '2px',
                boxShadow: editorMode === mode ? `0 0 10px ${mode === 'LIVE' ? '#28a745' : mode === 'BUILD' ? '#d22020' : '#fcd000'}, inset 2px 2px 4px rgba(255,255,255,0.4)` : 'inset 2px 2px 5px #000',
                border: '1px solid rgba(0,0,0,0.8)',
                transition: 'all 0.2s ease'
              }}>
              {mode}
            </div>
          ))}
        </div>
      </GridSpot>



      {/* SVG Wiring Layer */}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 2 }}>
        <defs>
          <filter id="drop-shadow-wire" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="3" dy="5" stdDeviation="3" floodColor="#000" floodOpacity="0.7" />
          </filter>
        </defs>
        {/* Cable 1: From h00 left edge to Inspector top-left hole */}
        <Cable
          start={[2.5, 3]}
          end={[2.5, 6.5]}
          cp1={[1, 3]}
          cp2={[1, 6.5]}
        />
        {/* Cable 2: From v4 bottom edge to Inspector right hole */}
        <Cable
          start={[46, 21.5]}
          end={[21.5, 21.5]}
          cp1={[46, 26]}
          cp2={[30, 21.5]}
        />
        {/* Cable 3: From v2 bottom edge to Inspector bottom hole */}
        <Cable
          start={[32, 24.5]}
          end={[16.5, 26.5]}
          cp1={[32, 28]}
          cp2={[16.5, 30]}
        />
        {/* Cable 4: From h10 left edge to Inspector right hole */}
        <Cable
          start={[23.5, 20]}
          end={[21.5, 19.5]}
          cp1={[22, 20]}
          cp2={[22, 19.5]}
        />
        {/* Cable 5: From v1 top edge to Inspector top hole */}
        <Cable
          start={[24, 2.5]}
          end={[16.5, 5.5]}
          cp1={[24, -0.5]}
          cp2={[16.5, -0.5]}
        />
      </svg>

      {/* Junction Boxes at Intersections */}
      {junctions.map((j, i) => (
        <GridSpot key={`junc-${i}`} col={j.col} row={j.row} style={{ zIndex: 8 }}>
          <div className="rogue-piece" style={{
            width: 'calc(2 * var(--stud))',
            height: 'calc(2 * var(--stud))',
            backgroundColor: '#2a2d32', // Dark grey junction brick
            backgroundImage: 'var(--highlight), var(--shadow)',
            backgroundSize: 'var(--stud) var(--stud)',
            boxShadow: '3px 3px 10px rgba(0,0,0,0.8)',
            borderTop: '2px solid rgba(255,255,255,0.2)',
            borderLeft: '2px solid rgba(255,255,255,0.1)',
            borderBottom: '2px solid rgba(0,0,0,0.8)',
            borderRight: '2px solid rgba(0,0,0,0.6)',
            borderRadius: '2px'
          }}></div>
        </GridSpot>
      ))}

      {/* Segments Map */}
      {segments.map(seg => {
        const isSelected = selectedSegId === seg.id;

        return (
          <GridSpot key={seg.id} col={seg.col} row={seg.row}>
            <div
              className={`rogue-piece interactive-segment ${isSelected ? 'segment-selected' : ''} ${getModeClass(seg.mode)}`}
              onClick={() => {
                setSelectedSegId(seg.id);
                sendInstruction({ page: 'topology', action: 'select_segment', payload: { segmentId: seg.id } });
              }}
              style={{
                zIndex: isSelected ? 20 : 10,
                width: `${LEGO_MATH.physicalSize(seg.w)}px`,
                height: `${LEGO_MATH.physicalSize(seg.h)}px`,
                backgroundColor: seg.color,
                // Do NOT set inline backgroundImage so the CSS animations can override it!
                cursor: 'pointer',
                border: isSelected ? '2px solid white' : 'none',
                boxShadow: isSelected ? `0 0 20px ${seg.color}` : 'none'
              }}
            >
              {/* Stud overlay so studs remain visible over the CSS animations */}
              <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', backgroundImage: `var(--highlight), var(--shadow)`, backgroundSize: 'var(--stud) var(--stud)', zIndex: 5 }}></div>

              {/* Trans-Neon Glassy Bevel Reflection */}
              <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 6,
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0) 25%, rgba(0,0,0,0) 75%, rgba(0,0,0,0.5) 100%)',
                boxShadow: 'inset 2px 2px 5px rgba(255,255,255,0.6), inset -2px -2px 5px rgba(0,0,0,0.5)',
                borderRadius: '2px'
              }}></div>

              {/* Physical Printed White Tile Label instead of OLED screen */}
              <div className="rogue-piece" style={{
                position: 'absolute',
                top: '50%', left: '50%',
                transform: seg.orientation === 'vertical' ? 'translate(-50%, -50%) rotate(-90deg)' : 'translate(-50%, -50%)',
                width: 'calc(6 * var(--stud))',
                height: 'calc(1 * var(--stud))',
                backgroundColor: '#f4f4f4', // Classic White Lego plastic
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.8) 0%, rgba(0,0,0,0.1) 100%)',
                borderTop: '2px solid rgba(255,255,255,1)',
                borderLeft: '2px solid rgba(255,255,255,0.8)',
                borderBottom: '2px solid rgba(0,0,0,0.5)',
                borderRight: '2px solid rgba(0,0,0,0.3)',
                borderRadius: '2px', // Smooth flat tile look
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                zIndex: 10,
                boxShadow: '2px 2px 5px rgba(0,0,0,0.6), 0 0 15px rgba(0,0,0,0.8)' // strong shadow against the glowing background
              }}>
                <span 
                  onClick={(e) => handleDirectionToggle(e, seg.id)}
                  style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', fontSize: '0.55rem', letterSpacing: '0.5px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ fontSize: '0.7rem' }}>{(seg as any).direction === 'UP' ? '▲' : '▼'}</span>
                  {seg.mode.toUpperCase()}
                </span>
              </div>
            </div>
          </GridSpot>
        );
      })}



      {/* LEFT Side: The Inspector Panel placed in the bottom-left empty space */}
      {/* Background Plate - Distinctive Technic Plate with Holes */}
      <GridSpot col={INSPECTOR_OFFSET_C} row={INSPECTOR_OFFSET_R}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(20)}px`,
          height: `${LEGO_MATH.physicalSize(22)}px`,
          backgroundColor: '#d22020',
          backgroundImage: `
            var(--highlight),
            radial-gradient(circle at 15px 15px, #e02b1f 0%, #e02b1f 7px, rgba(0, 0, 0, 0.5) 9px, transparent 10px),
            var(--shadow)
          `,
          backgroundSize: 'var(--stud) var(--stud)',
          borderTop: '2px solid rgba(255,255,255,0.4)',
          borderLeft: '2px solid rgba(255,255,255,0.2)',
          borderBottom: '2px solid rgba(0,0,0,0.8)',
          borderRight: '2px solid rgba(0,0,0,0.6)',
          borderRadius: '4px',
          boxShadow: '10px 10px 30px rgba(0,0,0,0.8)'
        }}></div>
      </GridSpot>

      {/* Technic Pins in the 4 corners of the red baseplate */}
      {[{ c: 0, r: 0 }, { c: 19, r: 0 }, { c: 0, r: 21 }, { c: 19, r: 21 }].map((pos, i) => (
        <GridSpot key={`pin-${i}`} col={INSPECTOR_OFFSET_C + pos.c} row={INSPECTOR_OFFSET_R + pos.r} style={{ zIndex: 2 }}>
          <div style={{ width: '30px', height: '30px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{
              width: '18px', height: '18px', borderRadius: '50%',
              backgroundColor: '#1a1a1a', // dark grey pin
              boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.3), inset -2px -2px 4px rgba(0,0,0,0.8), 2px 2px 3px rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              {/* Cross Axle shape inside pin */}
              <div style={{ position: 'relative', width: '10px', height: '10px' }}>
                <div style={{ position: 'absolute', top: '3.5px', left: '0px', width: '10px', height: '3px', backgroundColor: '#050505', boxShadow: 'inset 1px 1px 1px rgba(0,0,0,1)' }}></div>
                <div style={{ position: 'absolute', top: '0px', left: '3.5px', width: '3px', height: '10px', backgroundColor: '#050505', boxShadow: 'inset 1px 1px 1px rgba(0,0,0,1)' }}></div>
              </div>
            </div>
          </div>
        </GridSpot>
      ))}

      {/* Inset Screen Area with Brick-Built Bezel for Modes */}
      <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 4} style={{ zIndex: 5 }}>
        <div className="custom-scrollbar" style={{
          width: `${LEGO_MATH.physicalSize(18)}px`,
          height: `${LEGO_MATH.physicalSize(8)}px`,
          backgroundColor: '#0a0a0a',
          border: 'calc(0.4 * var(--stud)) solid #2a2d32',
          borderTopColor: '#3a3f44', // Lighter top for a physical bevel
          borderBottomColor: '#1a1f24', // Darker bottom
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
          {/* Inspector Modes - placed inside the screen */}
          {AVAILABLE_MODES.map((mode) => {
            const isCurrent = mode === selectedSeg.mode;
            return (
              <div key={mode} style={{ display: 'flex', gap: '6px', alignItems: 'center', cursor: 'pointer', width: 'calc(50% - 5px)' }} onClick={() => handleModeSelect(mode)}>
                {/* LED Radio Indicator */}
                <div style={{
                  width: '14px', height: '14px', borderRadius: '50%', flexShrink: 0,
                  backgroundColor: isCurrent ? selectedSeg.color : '#222',
                  boxShadow: isCurrent ? `0 0 10px ${selectedSeg.color}, inset 2px 2px 4px rgba(255,255,255,0.8)` : 'inset 2px 2px 4px rgba(0,0,0,0.8), 1px 1px 2px rgba(255,255,255,0.1)',
                  border: '1px solid rgba(0,0,0,0.5)',
                }}></div>

                {/* Printed Flat Tile */}
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
                  borderRadius: '2px', // Smooth flat tile look
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: isCurrent ? '#000' : '#fff',
                  fontSize: '0.55rem', fontWeight: 'bold',
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

      {/* Configuration Name Input Inset */}
      <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 13} style={{ zIndex: 7, transition: 'filter 0.3s ease', pointerEvents: editorMode === 'LIVE' ? 'none' : 'auto', filter: editorMode === 'LIVE' ? 'brightness(0.5)' : 'none' }}>
        <div style={{
          width: `${LEGO_MATH.physicalSize(18)}px`,
          height: `${LEGO_MATH.physicalSize(2)}px`,
          backgroundColor: '#0a0a0a',
          border: 'calc(0.2 * var(--stud)) solid #a0a5a9',
          borderTopColor: '#dcdcdc',
          borderBottomColor: '#646464',
          borderLeftColor: '#c8c8c8',
          borderRightColor: '#787878',
          borderRadius: '4px',
          boxShadow: editorMode !== 'LIVE' ? 'inset 4px 4px 15px rgba(0,0,0,0.9), inset 0 0 15px rgba(252, 208, 0, 0.1), 0 0 20px rgba(252, 208, 0, 0.2), 4px 4px 10px rgba(0,0,0,0.6)' : 'inset 4px 4px 15px rgba(0,0,0,0.9), 4px 4px 10px rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '0 10px',
          boxSizing: 'border-box',
          position: 'relative'
        }}>
          <div className="lcd-screen-fx" style={{ width: '100%', position: 'relative', display: 'flex', justifyContent: 'center' }}>
            {editorMode === 'MODIFY' ? (
              <select
                value={configName}
                onChange={handleConfigSelect}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#fcd000',
                  fontFamily: 'monospace',
                  fontSize: '1rem',
                  fontWeight: 'bold',
                  textShadow: '0 0 8px rgba(252, 208, 0, 0.6)',
                  width: '100%',
                  textAlign: 'center',
                  outline: 'none',
                  letterSpacing: '1px',
                  appearance: 'none',
                  cursor: 'pointer'
                }}
              >
                <option value="" disabled style={{ background: '#0a0a0a' }}>[SELECT CONFIG]</option>
                {(apiConfigurations[playlist] || []).map((cfg: any) => (
                  <option key={cfg.name} value={cfg.name} style={{ background: '#0a0a0a', color: '#fcd000' }}>
                    {cfg.name}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={configName}
                onChange={(e) => setConfigName(e.target.value)}
                placeholder="[CONFIG NAME]"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#fcd000',
                  fontFamily: 'monospace',
                  fontSize: '1rem',
                  fontWeight: 'bold',
                  textShadow: '0 0 8px rgba(252, 208, 0, 0.6)',
                  width: '100%',
                  textAlign: 'center',
                  outline: 'none',
                  letterSpacing: '1px'
                }}
              />
            )}
          </div>
          {editorMode === 'MODIFY' && (
            <div style={{ position: 'absolute', right: '15px', color: '#fcd000', pointerEvents: 'none', fontSize: '0.6rem' }}>▼</div>
          )}
        </div>
      </GridSpot>

      {/* Playlist Selection Inset */}
      <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 16} style={{ zIndex: 7, transition: 'filter 0.3s ease', pointerEvents: editorMode === 'LIVE' ? 'none' : 'auto', filter: editorMode === 'LIVE' ? 'brightness(0.5)' : 'none' }}>
        <div style={{
          width: `${LEGO_MATH.physicalSize(18)}px`,
          height: `${LEGO_MATH.physicalSize(5)}px`,
          backgroundColor: '#0a0a0a',
          border: 'calc(0.2 * var(--stud)) solid #a0a5a9',
          borderTopColor: '#dcdcdc',
          borderBottomColor: '#646464',
          borderLeftColor: '#c8c8c8',
          borderRightColor: '#787878',
          borderRadius: '4px',
          boxShadow: 'inset 4px 4px 15px rgba(0,0,0,0.9), 4px 4px 10px rgba(0,0,0,0.6)',
          display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'space-evenly',
          padding: '0 10px',
          boxSizing: 'border-box',
          position: 'relative'
        }}>
          
          {/* LED Status Light */}
          <div style={{
            position: 'absolute', top: '12px', left: '15px',
            width: '14px', height: '14px', borderRadius: '50%',
            backgroundColor: playlist === 'PLAYLIST_A' ? '#00ffff' : '#ff00ff',
            boxShadow: `inset 2px 2px 4px rgba(255,255,255,0.8), inset -2px -2px 4px rgba(0,0,0,0.5), 0 0 10px ${playlist === 'PLAYLIST_A' ? '#00ffff' : '#ff00ff'}`,
            border: '1px solid rgba(0,0,0,0.8)'
          }}></div>

          {/* Playlist Info */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '50%' }}>
            <div style={{ color: '#888', fontSize: '0.6rem', fontWeight: 'bold', letterSpacing: '1px', marginBottom: '4px' }}>PLAYLIST</div>
            <div className="lcd-screen-fx" style={{
              width: '100%', height: '24px', backgroundColor: '#050505',
              color: '#00ffff', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontFamily: 'monospace', fontSize: '0.7rem', textAlign: 'center',
              boxShadow: 'inset 0 0 8px #000, 0 0 10px rgba(0, 255, 255, 0.2)', border: '1px solid #222',
              textShadow: '0 0 5px #00ffff', borderRadius: '2px'
            }}>
              {playlist}
            </div>
          </div>

          {/* Cycle Buttons */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button className="cheese-slope-btn left" onClick={() => handlePlaylistCycle(-1)}>{"<"}</button>
            <button className="cheese-slope-btn right" onClick={() => handlePlaylistCycle(1)}>{">"}</button>
          </div>

          {/* Save Button (1x1 Round Plate) */}
          <button onClick={handleSave} style={{
            position: 'relative',
            width: '45px', height: '45px', borderRadius: '50%', border: 'none', outline: 'none',
            backgroundColor: editorMode === 'BUILD' ? '#da291c' : '#ffcd00', 
            cursor: 'pointer',
            boxShadow: `inset 2px 2px 4px rgba(255,255,255,0.6), inset -2px -2px 6px rgba(0,0,0,0.4), 3px 3px 6px rgba(0,0,0,0.8), 0 0 15px ${editorMode === 'BUILD' ? 'rgba(218,41,28,0.8)' : 'rgba(255,205,0,0.8)'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#000', fontWeight: '900', fontSize: '0.6rem', letterSpacing: '0px', transition: 'all 0.1s ease', zIndex: 10
          }}
          onMouseDown={(e) => e.currentTarget.style.transform = 'translateY(2px)'}
          onMouseUp={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{
              position: 'absolute', width: '28px', height: '28px', borderRadius: '50%',
              backgroundColor: editorMode === 'BUILD' ? '#da291c' : '#ffcd00',
              boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.7), inset -1px -1px 3px rgba(0,0,0,0.3), 1px 1px 3px rgba(0,0,0,0.5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <span style={{ position: 'relative', zIndex: 10, opacity: 0.8 }}>{editorMode === 'BUILD' ? 'SAVE' : 'UPD'}</span>
            </div>
          </button>
        </div>
      </GridSpot>

      {/* Sticker Decal Title */}
      <GridSpot col={INSPECTOR_OFFSET_C + 5} row={INSPECTOR_OFFSET_R + 3} style={{ zIndex: 10 }}>
        <div className="rogue-piece" style={{
          width: 'calc(10 * var(--stud))',
          height: 'calc(1 * var(--stud))',
          backgroundColor: '#fcd000', // Classic Lego Yellow
          backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.4) 0%, rgba(0,0,0,0.1) 100%)',
          borderTop: '2px solid rgba(255,255,255,0.6)',
          borderLeft: '2px solid rgba(255,255,255,0.3)',
          borderBottom: '2px solid rgba(0,0,0,0.4)',
          borderRight: '2px solid rgba(0,0,0,0.2)',
          borderRadius: '2px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '2px 2px 5px rgba(0,0,0,0.5)',
          overflow: 'hidden',
          position: 'relative'
        }}>
          {/* Hazard stripes on left/right */}
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }}></div>
          <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }}></div>

          <span style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', letterSpacing: '1px', fontSize: '0.8rem', zIndex: 2 }}>
            SYSTEM MODES
          </span>
        </div>
      </GridSpot>

      <GridSpot col={INSPECTOR_OFFSET_C + 1} row={INSPECTOR_OFFSET_R + 1} style={{ zIndex: 10 }}>
        <div style={{
          width: 'calc(18 * var(--stud))',
          height: 'calc(1 * var(--stud))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {Array.from({ length: 18 }).map((_, i) => {
            const name = selectedSeg.name.toUpperCase().replace('_', ' ');
            const startIdx = Math.floor((18 - name.length) / 2);
            const char = (i >= startIdx && i < startIdx + name.length) ? name[i - startIdx] : '';

            const angle = (Math.sin(i * 13.37) * 3.5).toFixed(1); // Pseudo-random angle between -3.5 and 3.5 degrees

            return (
              <div key={i} className="rogue-piece" style={{
                position: 'relative',
                transform: `rotate(${angle}deg)`,
                width: 'calc(1 * var(--stud))',
                height: 'calc(1 * var(--stud))',
                backgroundColor: '#4a4f54', // Dark grey tile
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(0,0,0,0.2) 100%)',
                borderTop: '2px solid rgba(255,255,255,0.3)',
                borderLeft: '2px solid rgba(255,255,255,0.1)',
                borderBottom: '2px solid rgba(0,0,0,0.6)',
                borderRight: '2px solid rgba(0,0,0,0.4)',
                borderRadius: '2px', // Smooth flat tile look
                display: 'flex', alignItems: 'center', justifyContent: 'center',
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
        <div style={{
          width: 'calc(18 * var(--stud))',
          height: 'calc(1 * var(--stud))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {Array.from({ length: 18 }).map((_, i) => {
            const str = `MODE: ${selectedSeg.mode.toUpperCase()}`;
            const startIdx = Math.max(0, Math.floor((18 - str.length) / 2));
            const char = (i >= startIdx && i < startIdx + str.length) ? str[i - startIdx] : '';

            // Give it a slightly different seed so it doesn't match the segment name angles exactly
            const angle = (Math.sin((i + 18) * 17.43) * 3.5).toFixed(1);

            // First 6 characters are "MODE: ", which we color white. The rest is yellow.
            const isModeText = i >= startIdx + 6;
            const textColor = isModeText ? 'var(--lego-yellow)' : 'white';
            const shadowColor = isModeText ? 'var(--lego-yellow)' : 'rgba(255,255,255,0.5)';

            return (
              <div key={i} className="rogue-piece" style={{
                position: 'relative',
                transform: `rotate(${angle}deg)`,
                width: 'calc(1 * var(--stud))',
                height: 'calc(1 * var(--stud))',
                backgroundColor: '#111', // Dark smooth black tile
                backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(0,0,0,0.4) 100%)',
                borderTop: '2px solid rgba(255,255,255,0.2)',
                borderLeft: '2px solid rgba(255,255,255,0.1)',
                borderBottom: '2px solid rgba(0,0,0,0.8)',
                borderRight: '2px solid rgba(0,0,0,0.6)',
                borderRadius: '2px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
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



    </div>
  );
};
