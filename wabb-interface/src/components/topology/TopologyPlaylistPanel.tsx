import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { INSPECTOR_OFFSET_C, INSPECTOR_OFFSET_R } from '../../constants/topologyData';
import type { EditorMode } from './types';

export const TopologyPlaylistPanel = ({
  editorMode,
  playlist,
  playlistNameDraft,
  playlistLightColor,
  isSaving,
  onPlaylistNameChange,
  onCreatePlaylist,
  onRenamePlaylist,
  onDeletePlaylist,
  onPlaylistCycle,
}: {
  editorMode: EditorMode;
  playlist: string;
  playlistNameDraft: string;
  playlistLightColor: string;
  isSaving: boolean;
  onPlaylistNameChange: (value: string) => void;
  onCreatePlaylist: () => void;
  onRenamePlaylist: () => void;
  onDeletePlaylist: () => void;
  onPlaylistCycle: (direction: 1 | -1) => void;
}) => (
  <GridSpot
    col={INSPECTOR_OFFSET_C + 1}
    row={INSPECTOR_OFFSET_R + 17}
    style={{ zIndex: 7, transition: 'filter 0.3s ease', pointerEvents: editorMode === 'LIVE' ? 'none' : 'auto', filter: editorMode === 'LIVE' ? 'brightness(0.5)' : 'none' }}
  >
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
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-evenly',
      padding: '0 10px',
      boxSizing: 'border-box',
      position: 'relative'
    }}>
      <div style={{
        position: 'absolute',
        top: '12px',
        left: '15px',
        width: '14px',
        height: '14px',
        borderRadius: '50%',
        backgroundColor: playlistLightColor,
        boxShadow: `inset 2px 2px 4px rgba(255,255,255,0.8), inset -2px -2px 4px rgba(0,0,0,0.5), 0 0 10px ${playlistLightColor}`,
        border: '1px solid rgba(0,0,0,0.8)'
      }} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '58%', gap: '5px' }}>
        <div style={{ color: '#888', fontSize: '0.6rem', fontWeight: 'bold', letterSpacing: '1px', marginBottom: '4px' }}>PLAYLIST</div>
        <div className="lcd-screen-fx" style={{
          width: '100%',
          height: '22px',
          backgroundColor: '#050505',
          color: '#00ffff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'monospace',
          fontSize: '0.7rem',
          textAlign: 'center',
          boxShadow: 'inset 0 0 8px #000, 0 0 10px rgba(0, 255, 255, 0.2)',
          border: '1px solid #222',
          textShadow: '0 0 5px #00ffff',
          borderRadius: '2px'
        }}>
          {playlist || '[NO PLAYLIST]'}
        </div>
        <input
          type="text"
          value={playlistNameDraft}
          onChange={(event) => onPlaylistNameChange(event.target.value)}
          placeholder="[PLAYLIST NAME]"
          disabled={isSaving}
          style={{
            width: '100%',
            height: '22px',
            backgroundColor: '#050505',
            border: '1px solid #333',
            borderRadius: '2px',
            boxSizing: 'border-box',
            color: '#fcd000',
            fontFamily: 'monospace',
            fontSize: '0.65rem',
            fontWeight: 'bold',
            letterSpacing: '0.5px',
            outline: 'none',
            padding: '0 7px',
            textAlign: 'center',
            textShadow: '0 0 6px rgba(252, 208, 0, 0.5)',
            opacity: isSaving ? 0.6 : 1,
          }}
        />
        <div style={{ display: 'flex', gap: '4px', width: '100%', flexWrap: 'wrap' }}>
          {[
            { label: 'NEW', onClick: onCreatePlaylist, color: '#28a745', fg: '#000' as const },
            { label: 'REN', onClick: onRenamePlaylist, color: '#fcd000', fg: '#000' as const },
            { label: 'DEL', onClick: onDeletePlaylist, color: '#d22020', fg: '#fff' as const },
          ].map(action => (
            <button
              key={action.label}
              onClick={action.onClick}
              disabled={isSaving}
              style={{
                flex: '1 1 28%',
                minWidth: '0',
                height: '22px',
                border: '1px solid rgba(0,0,0,0.8)',
                borderRadius: '2px',
                backgroundColor: action.color,
                color: action.fg,
                cursor: isSaving ? 'not-allowed' : 'pointer',
                fontSize: '0.55rem',
                fontWeight: '900',
                letterSpacing: '1px',
                boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.5), inset -2px -2px 3px rgba(0,0,0,0.35), 2px 2px 4px rgba(0,0,0,0.7)',
                opacity: isSaving ? 0.6 : 1,
              }}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <button className="cheese-slope-btn left" disabled={isSaving} onClick={() => onPlaylistCycle(-1)}>{'<'}</button>
        <button className="cheese-slope-btn right" disabled={isSaving} onClick={() => onPlaylistCycle(1)}>{'>'}</button>
      </div>
    </div>
  </GridSpot>
);
