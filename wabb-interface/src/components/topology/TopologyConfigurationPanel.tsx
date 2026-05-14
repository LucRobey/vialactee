import type { ChangeEvent } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { GridSpot } from '../layout/GridSpot';
import { CONFIGURATOR_OFFSET_C, CONFIGURATOR_OFFSET_R } from '../../constants/topologyData';
import type { SegmentConfiguration } from '../../utils/configurationStore';
import type { EditorMode } from './types';

export const TopologyConfigurationPanel = ({
  editorMode,
  playlist,
  apiConfigurations,
  selectedConfigName,
  configName,
  isSaving,
  onConfigSelect,
  onConfigNameChange,
  onRenameConfiguration,
  onDeleteConfiguration,
  onSave,
}: {
  editorMode: EditorMode;
  playlist: string;
  apiConfigurations: Record<string, SegmentConfiguration[]>;
  selectedConfigName: string;
  configName: string;
  isSaving: boolean;
  onConfigSelect: (event: ChangeEvent<HTMLSelectElement>) => void;
  onConfigNameChange: (value: string) => void;
  onRenameConfiguration: () => void;
  onDeleteConfiguration: () => void;
  onSave: () => void;
}) => {
  const playlistConfigs = Object.entries(apiConfigurations).find(([name]) => name.trim().toLowerCase() === playlist.trim().toLowerCase())?.[1] || [];
  const effectiveSelectedConfigName = playlistConfigs.some(cfg => cfg.name === selectedConfigName)
    ? selectedConfigName
    : (playlistConfigs[0]?.name ?? '');
  return (
  <GridSpot
    col={CONFIGURATOR_OFFSET_C + 1}
    row={CONFIGURATOR_OFFSET_R + 1}
    style={{ zIndex: 7, transition: 'filter 0.3s ease', pointerEvents: editorMode === 'LIVE' ? 'none' : 'auto', filter: editorMode === 'LIVE' ? 'brightness(0.5)' : 'none' }}
  >
    <div style={{
      width: `${LEGO_MATH.physicalSize(18)}px`,
      height: `${LEGO_MATH.physicalSize(10)}px`,
      backgroundColor: '#0a0a0a',
      border: 'calc(0.2 * var(--stud)) solid #a0a5a9',
      borderTopColor: '#dcdcdc',
      borderBottomColor: '#646464',
      borderLeftColor: '#c8c8c8',
      borderRightColor: '#787878',
      borderRadius: '4px',
      boxShadow: editorMode !== 'LIVE' ? 'inset 4px 4px 15px rgba(0,0,0,0.9), inset 0 0 15px rgba(252, 208, 0, 0.1), 0 0 20px rgba(252, 208, 0, 0.2), 4px 4px 10px rgba(0,0,0,0.6)' : 'inset 4px 4px 15px rgba(0,0,0,0.9), 4px 4px 10px rgba(0,0,0,0.6)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start',
      padding: '10px',
      boxSizing: 'border-box',
      position: 'relative',
      gap: '8px'
    }}>
      <div className="lcd-screen-fx" style={{ width: '100%', position: 'relative', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: '6px' }}>
        {editorMode === 'MODIFY' ? (
          <>
            <select
              value={effectiveSelectedConfigName}
              onChange={onConfigSelect}
              disabled={isSaving}
              style={{
                background: '#050505',
                border: '1px solid #333',
                borderRadius: '2px',
                color: '#00ffff',
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                textShadow: '0 0 8px rgba(0, 255, 255, 0.6)',
                width: '100%',
                height: '24px',
                textAlign: 'center',
                outline: 'none',
                letterSpacing: '1px',
                appearance: 'none',
                cursor: isSaving ? 'not-allowed' : 'pointer',
                opacity: isSaving ? 0.6 : 1,
              }}
            >
              <option value="" disabled style={{ background: '#0a0a0a' }}>[SELECT CONFIG]</option>
              {playlistConfigs.map((cfg) => (
                <option key={cfg.name} value={cfg.name} style={{ background: '#0a0a0a', color: '#fcd000' }}>
                  {cfg.name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={configName}
              onChange={(event) => onConfigNameChange(event.target.value)}
              placeholder="[CONFIG NAME]"
              disabled={isSaving}
              style={{
                background: '#050505',
                border: '1px solid #333',
                borderRadius: '2px',
                color: '#fcd000',
                fontFamily: 'monospace',
                fontSize: '0.8rem',
                fontWeight: 'bold',
                textShadow: '0 0 8px rgba(252, 208, 0, 0.6)',
                width: '100%',
                height: '24px',
                textAlign: 'center',
                outline: 'none',
                letterSpacing: '1px',
                boxSizing: 'border-box',
                opacity: isSaving ? 0.6 : 1,
              }}
            />
            <div style={{ display: 'flex', gap: '6px', width: '100%' }}>
              {[
                { label: 'REN', onClick: onRenameConfiguration, color: '#fcd000' },
                { label: 'DEL', onClick: onDeleteConfiguration, color: '#d22020' },
              ].map(action => (
                <button
                  key={action.label}
                  onClick={action.onClick}
                  disabled={isSaving}
                  style={{
                    flex: 1,
                    height: '22px',
                    border: '1px solid rgba(0,0,0,0.8)',
                    borderRadius: '2px',
                    backgroundColor: action.color,
                    color: action.label === 'DEL' ? '#fff' : '#000',
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
          </>
        ) : (
          <input
            type="text"
            value={configName}
            onChange={(event) => onConfigNameChange(event.target.value)}
            placeholder="[CONFIG NAME]"
            disabled={isSaving}
            style={{
              background: '#050505',
              border: '1px solid #333',
              borderRadius: '2px',
              color: '#fcd000',
              fontFamily: 'monospace',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              textShadow: '0 0 8px rgba(252, 208, 0, 0.6)',
              width: '100%',
              height: '24px',
              textAlign: 'center',
              outline: 'none',
              letterSpacing: '1px',
              boxSizing: 'border-box',
              opacity: isSaving ? 0.6 : 1,
            }}
          />
        )}

        <button
          onClick={onSave}
          disabled={isSaving}
          style={{
            alignSelf: 'center',
            position: 'relative',
            width: '45px',
            height: '45px',
            borderRadius: '50%',
            border: 'none',
            outline: 'none',
            backgroundColor: editorMode === 'BUILD' ? '#da291c' : '#ffcd00',
            cursor: isSaving ? 'not-allowed' : 'pointer',
            boxShadow: editorMode === 'BUILD'
              ? 'inset 2px 2px 4px rgba(255,255,255,0.6), inset -2px -2px 6px rgba(0,0,0,0.4), 3px 3px 6px rgba(0,0,0,0.8), 0 0 15px rgba(218,41,28,0.8)'
              : 'inset 2px 2px 4px rgba(255,255,255,0.6), inset -2px -2px 6px rgba(0,0,0,0.4), 3px 3px 6px rgba(0,0,0,0.8), 0 0 15px rgba(255,205,0,0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#000',
            fontWeight: '900',
            fontSize: '0.6rem',
            letterSpacing: '0px',
            transition: 'all 0.1s ease',
            zIndex: 10,
            opacity: isSaving ? 0.6 : 1,
          }}
        >
          <div style={{
            position: 'absolute',
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            backgroundColor: editorMode === 'BUILD' ? '#da291c' : '#ffcd00',
            boxShadow: 'inset 1px 1px 2px rgba(255,255,255,0.7), inset -1px -1px 3px rgba(0,0,0,0.3), 1px 1px 3px rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <span style={{ position: 'relative', zIndex: 10, opacity: 0.8 }}>
              {isSaving ? '...' : editorMode === 'BUILD' ? 'SAVE' : 'UPD'}
            </span>
          </div>
        </button>
      </div>
      
      <div className="custom-scrollbar" style={{
        width: '100%',
        flex: 1,
        backgroundColor: '#050505',
        border: '1px solid #333',
        borderRadius: '2px',
        padding: '4px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px'
      }}>
        {playlistConfigs.map((cfg) => {
          const isSelected = cfg.name === effectiveSelectedConfigName;
          return (
            <div
              key={cfg.name}
              onClick={() => !isSaving && onConfigSelect({ target: { value: cfg.name } } as any)}
              style={{
                padding: '4px 8px',
                backgroundColor: isSelected ? '#1a1a1a' : 'transparent',
                color: isSelected ? '#00ffff' : '#888',
                fontFamily: 'monospace',
                fontSize: '0.65rem',
                fontWeight: isSelected ? 'bold' : 'normal',
                cursor: isSaving ? 'not-allowed' : 'pointer',
                borderRadius: '2px',
                border: isSelected ? '1px solid #00ffff44' : '1px solid transparent',
                textShadow: isSelected ? '0 0 5px #00ffff88' : 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <div style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: isSelected ? '#00ffff' : '#444',
                boxShadow: isSelected ? '0 0 5px #00ffff' : 'none'
              }} />
              {cfg.name.toUpperCase()}
            </div>
          );
        })}
        {playlistConfigs.length === 0 && (
          <div style={{ color: '#444', fontSize: '0.6rem', textAlign: 'center', marginTop: '10px', fontFamily: 'monospace' }}>
            [EMPTY PLAYLIST]
          </div>
        )}
      </div>

      {editorMode === 'MODIFY' && (
        <div style={{ position: 'absolute', right: '15px', top: '18px', color: '#00ffff', pointerEvents: 'none', fontSize: '0.6rem' }}>▼</div>
      )}
    </div>
  </GridSpot>
  );
};
