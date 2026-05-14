import { useEffect, useRef, useState } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { FitBoard } from '../layout/FitBoard';
import { GridSpot } from '../layout/GridSpot';
import {
  sendInstruction,
  subscribeModeMasterState,
  type ModeMasterState,
  type ModeSettingDescriptor,
  type ModeSettingValue,
  type ModeSettingsCatalogEntry,
} from '../../utils/controlBridge';
import { useBridgeStatus } from '../../utils/useBridgeStatus';

type PendingModeSettings = Record<string, Record<string, ModeSettingValue>>;

const PANEL_COL = 4;
const PANEL_ROW = 2;
const SCREEN_WIDTH = 44;
const BOARD_WIDTH = LEGO_MATH.physicalSize(52);
const BOARD_HEIGHT = LEGO_MATH.grid(35);

const valuesMatch = (a: ModeSettingValue | undefined, b: ModeSettingValue | undefined) => {
  if (typeof a === 'number' && typeof b === 'number') {
    return Math.abs(a - b) < 0.000001;
  }
  return a === b;
};

const coerceValue = (descriptor: ModeSettingDescriptor, rawValue: string | boolean): ModeSettingValue => {
  if (descriptor.valueType === 'boolean') {
    return Boolean(rawValue);
  }

  if (descriptor.valueType === 'number') {
    const numericValue = Number(rawValue);
    return descriptor.integer ? Math.round(numericValue) : numericValue;
  }

  return String(rawValue);
};

const formatValueLabel = (descriptor: ModeSettingDescriptor, value: ModeSettingValue) => {
  if (typeof value === 'number') {
    const rendered = descriptor.integer ? String(Math.round(value)) : value.toFixed(value % 1 === 0 ? 0 : 2);
    return descriptor.unit ? `${rendered}${descriptor.unit}` : rendered;
  }
  if (typeof value === 'boolean') {
    return value ? 'ON' : 'OFF';
  }
  return String(value).toUpperCase();
};

export const ModeSettings = () => {
  const [catalog, setCatalog] = useState<ModeSettingsCatalogEntry[]>([]);
  const [modeSettings, setModeSettings] = useState<Record<string, Record<string, ModeSettingValue>>>({});
  const pendingEditsRef = useRef<PendingModeSettings>({});
  const bridgeStatus = useBridgeStatus();

  useEffect(() => {
    return subscribeModeMasterState((state: ModeMasterState) => {
      setCatalog(Array.isArray(state.modeSettingsCatalog) ? state.modeSettingsCatalog : []);

      const nextSettings: Record<string, Record<string, ModeSettingValue>> = {};
      Object.entries(state.modeSettings || {}).forEach(([modeName, settings]) => {
        nextSettings[modeName] = { ...settings };
      });

      Object.entries(pendingEditsRef.current).forEach(([modeName, settings]) => {
        Object.entries(settings).forEach(([key, pendingValue]) => {
          const liveValue = state.modeSettings?.[modeName]?.[key];
          if (valuesMatch(liveValue, pendingValue)) {
            delete pendingEditsRef.current[modeName][key];
            if (Object.keys(pendingEditsRef.current[modeName]).length === 0) {
              delete pendingEditsRef.current[modeName];
            }
            return;
          }

          if (!nextSettings[modeName]) {
            nextSettings[modeName] = {};
          }
          nextSettings[modeName][key] = pendingValue;
        });
      });

      setModeSettings(nextSettings);
    });
  }, []);

  const visibleModes = catalog.filter((entry) => Array.isArray(entry.settings) && entry.settings.length > 0);

  const handleSettingChange = (modeName: string, descriptor: ModeSettingDescriptor, rawValue: string | boolean) => {
    const nextValue = coerceValue(descriptor, rawValue);

    if (!pendingEditsRef.current[modeName]) {
      pendingEditsRef.current[modeName] = {};
    }
    pendingEditsRef.current[modeName][descriptor.key] = nextValue;

    setModeSettings((prev) => ({
      ...prev,
      [modeName]: {
        ...(prev[modeName] || {}),
        [descriptor.key]: nextValue,
      },
    }));

    sendInstruction({
      page: 'mode_settings',
      action: 'set_mode_setting',
      payload: {
        mode: modeName,
        key: descriptor.key,
        value: nextValue,
      },
    });
  };

  return (
    <FitBoard width={BOARD_WIDTH} height={BOARD_HEIGHT}>
      <div style={{ position: 'relative', width: `${BOARD_WIDTH}px`, height: `${BOARD_HEIGHT}px` }}>
      <GridSpot col={PANEL_COL - 4} row={PANEL_ROW + 2}>
        <div className="rogue-piece dark-grey" style={{
          width: `${LEGO_MATH.physicalSize(8)}px`,
          height: `${LEGO_MATH.physicalSize(22)}px`,
          boxShadow: 'inset 0 0 30px #000, 6px 6px 15px rgba(0,0,0,0.55)'
        }}></div>
      </GridSpot>

      <GridSpot col={PANEL_COL} row={PANEL_ROW}>
        <div className="rogue-piece" style={{
          width: `${LEGO_MATH.physicalSize(48)}px`,
          height: `${LEGO_MATH.physicalSize(28)}px`,
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

      {[{ c: 0, r: 0 }, { c: 47, r: 0 }, { c: 0, r: 27 }, { c: 47, r: 27 }].map((pos, i) => (
        <GridSpot key={`mode-settings-pin-${i}`} col={PANEL_COL + pos.c} row={PANEL_ROW + pos.r} style={{ zIndex: 2 }}>
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

      <GridSpot col={PANEL_COL + 15} row={PANEL_ROW + 2} style={{ zIndex: 10 }}>
        <div className="rogue-piece" style={{
          width: 'calc(16 * var(--stud))',
          height: 'calc(1 * var(--stud))',
          backgroundColor: '#fcd000',
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
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }}></div>
          <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: '25px', backgroundImage: 'repeating-linear-gradient(45deg, #000, #000 4px, transparent 4px, transparent 8px)', opacity: 0.6 }}></div>

          <span style={{ color: '#000', fontWeight: '900', fontFamily: 'Arial, sans-serif', letterSpacing: '1px', fontSize: '0.82rem', zIndex: 2 }}>
            MODE SETTINGS
          </span>
        </div>
      </GridSpot>

      <GridSpot col={PANEL_COL + 2} row={PANEL_ROW + 3} style={{ zIndex: 10 }}>
        <div style={{
          width: `calc(${SCREEN_WIDTH} * var(--stud))`,
          height: 'calc(1 * var(--stud))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {Array.from({ length: SCREEN_WIDTH }).map((_, i) => {
            const str = 'LIVE MODE TUNING';
            const startIdx = Math.max(0, Math.floor((SCREEN_WIDTH - str.length) / 2));
            const char = (i >= startIdx && i < startIdx + str.length) ? str[i - startIdx] : '';
            const angle = (Math.sin((i + 11) * 17.43) * 3.5).toFixed(1);

            return (
              <div key={`mode-settings-char-${i}`} className="rogue-piece" style={{
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
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: char ? 'var(--lego-yellow)' : 'transparent',
                fontWeight: 'bold',
                fontFamily: 'monospace',
                fontSize: '1rem',
                textShadow: char ? '0 0 8px rgba(252,208,0,0.45)' : 'none',
                boxShadow: '1px 1px 4px rgba(0,0,0,0.8)',
                boxSizing: 'border-box'
              }}>
                {char !== ' ' ? char : ''}
              </div>
            );
          })}
        </div>
      </GridSpot>

      <GridSpot col={PANEL_COL + 2} row={PANEL_ROW + 5} style={{ zIndex: 5 }}>
        <div className="custom-scrollbar" style={{
          width: `${LEGO_MATH.physicalSize(SCREEN_WIDTH)}px`,
          height: `${LEGO_MATH.physicalSize(21)}px`,
          backgroundColor: '#0a0a0a',
          border: 'calc(0.4 * var(--stud)) solid #2a2d32',
          borderTopColor: '#3a3f44',
          borderBottomColor: '#1a1f24',
          borderLeftColor: '#30353a',
          borderRightColor: '#20252a',
          borderRadius: '4px',
          boxShadow: 'inset 4px 4px 15px rgba(0,0,0,0.9), 2px 2px 5px rgba(0,0,0,0.5)',
          boxSizing: 'border-box',
          padding: '12px',
          display: 'grid',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          alignContent: 'flex-start',
          gap: '10px 8px',
          overflowY: 'auto'
        }}>
          {visibleModes.length === 0 ? (
            <div style={{
              color: '#888',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              letterSpacing: '1px'
            }}>
              {bridgeStatus === 'open' ? '[NO MODES WITH SETTINGS]' : '[WAITING FOR LIVE CONTROLLER DATA]'}
            </div>
          ) : (
            visibleModes.map((entry) => (
              <div key={entry.mode} style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                padding: '8px',
                backgroundColor: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '4px',
                boxShadow: 'inset 0 0 10px rgba(0,0,0,0.35)'
              }}>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', width: '100%' }}>
                  <div style={{
                    width: '14px', height: '14px', borderRadius: '50%', flexShrink: 0,
                    backgroundColor: '#00ffff',
                    boxShadow: '0 0 10px rgba(0,255,255,0.65), inset 2px 2px 4px rgba(255,255,255,0.8)',
                    border: '1px solid rgba(0,0,0,0.5)',
                  }}></div>

                  <div className="rogue-piece" style={{
                    position: 'relative',
                    width: 'calc(100% - 20px)',
                    height: 'calc(1 * var(--stud))',
                    backgroundColor: '#fcd000',
                    backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(0,0,0,0.2) 100%)',
                    borderTop: '2px solid rgba(255,255,255,0.4)',
                    borderLeft: '2px solid rgba(255,255,255,0.2)',
                    borderBottom: '2px solid rgba(0,0,0,0.8)',
                    borderRight: '2px solid rgba(0,0,0,0.6)',
                    borderRadius: '2px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#000',
                    fontSize: '0.55rem', fontWeight: 'bold',
                    boxShadow: '2px 2px 4px rgba(0,0,0,0.6)',
                    boxSizing: 'border-box',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {entry.label.toUpperCase()}
                  </div>
                </div>

                {entry.settings.map((descriptor) => {
                  const currentValue = modeSettings[entry.mode]?.[descriptor.key] ?? descriptor.default;
                  const selectValue = typeof currentValue === 'boolean' ? String(currentValue) : String(currentValue);

                  return (
                    <div key={`${entry.mode}-${descriptor.key}`} style={{
                      backgroundColor: '#050505',
                      border: '1px solid #2a2d32',
                      borderRadius: '4px',
                      boxShadow: 'inset 0 0 8px #000',
                      padding: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '7px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', alignItems: 'center' }}>
                        <span style={{
                          color: '#f4f4f4',
                          fontWeight: '900',
                          fontSize: '0.68rem',
                          letterSpacing: '0.6px'
                        }}>
                          {descriptor.label.toUpperCase()}
                        </span>
                        <span style={{
                          color: '#00ffff',
                          fontWeight: 'bold',
                          fontFamily: 'monospace',
                          fontSize: '0.72rem',
                          textShadow: '0 0 8px rgba(0,255,255,0.45)'
                        }}>
                          {formatValueLabel(descriptor, currentValue)}
                        </span>
                      </div>

                      {descriptor.control === 'switch' ? (
                        <button
                          onClick={() => handleSettingChange(entry.mode, descriptor, !(currentValue as boolean))}
                          style={{
                            height: '30px',
                            border: '1px solid rgba(0,0,0,0.8)',
                            borderRadius: '2px',
                            backgroundColor: (currentValue as boolean) ? '#28a745' : '#2a2d32',
                            color: (currentValue as boolean) ? '#000' : '#fff',
                            cursor: 'pointer',
                            fontSize: '0.62rem',
                            fontWeight: '900',
                            letterSpacing: '1px',
                            boxShadow: (currentValue as boolean)
                              ? 'inset 1px 1px 2px rgba(255,255,255,0.5), inset -2px -2px 3px rgba(0,0,0,0.35), 0 0 10px rgba(40,167,69,0.35)'
                              : 'inset 2px 2px 5px rgba(0,0,0,0.65)'
                          }}
                        >
                          {(currentValue as boolean) ? 'ON' : 'OFF'}
                        </button>
                      ) : descriptor.control === 'list' ? (
                        <select
                          value={selectValue}
                          onChange={(event) => handleSettingChange(entry.mode, descriptor, event.target.value)}
                          style={{
                            background: '#050505',
                            border: '1px solid #333',
                            borderRadius: '2px',
                            color: '#fcd000',
                            fontFamily: 'monospace',
                            fontSize: '0.72rem',
                            fontWeight: 'bold',
                            width: '100%',
                            height: '28px',
                            outline: 'none',
                            letterSpacing: '0.5px',
                            appearance: 'none',
                            padding: '0 8px',
                            cursor: 'pointer'
                          }}
                        >
                          {(descriptor.options || []).map((option) => (
                            <option key={`${descriptor.key}-${String(option.value)}`} value={String(option.value)} style={{ background: '#0a0a0a', color: '#fcd000' }}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="range"
                          min={descriptor.min}
                          max={descriptor.max}
                          step={descriptor.step}
                          value={typeof currentValue === 'number' ? currentValue : Number(descriptor.default)}
                          onChange={(event) => handleSettingChange(entry.mode, descriptor, event.target.value)}
                          style={{ width: '100%', accentColor: '#00ffff' }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </GridSpot>
      </div>
    </FitBoard>
  );
};
