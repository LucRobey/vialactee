import { useEffect, useState, type CSSProperties } from 'react';
import { LEGO_MATH } from '../../utils/legoMath';
import { FitBoard } from '../layout/FitBoard';
import { GridSpot } from '../layout/GridSpot';
import { NoticeBanner } from '../common/NoticeBanner';
import { sendInstruction, subscribeModeMasterState, type SystemStatus } from '../../utils/controlBridge';
import { useBridgeStatus } from '../../utils/useBridgeStatus';

const OLED_STYLE: CSSProperties = {
  width: 'calc(11.5 * var(--stud))',
  height: 'calc(5 * var(--stud))',
  position: 'relative',
  top: 0,
  left: 0,
  transform: 'none',
  display: 'flex',
  flexDirection: 'column',
  padding: '8px 10px',
};

const PANEL_INSET_STYLE: CSSProperties = {
  width: '100%',
  height: '100%',
  background: 'linear-gradient(180deg, rgba(24,28,34,0.96) 0%, rgba(10,12,16,0.98) 100%)',
  borderRadius: '8px',
  border: '2px solid rgba(255,255,255,0.05)',
  boxShadow: 'inset 0 0 18px rgba(0,0,0,0.85), 0 10px 25px rgba(0,0,0,0.55)',
  padding: '10px 12px',
  boxSizing: 'border-box',
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const BOARD_WIDTH = LEGO_MATH.physicalSize(76);
const BOARD_HEIGHT = LEGO_MATH.grid(35);

const EMPTY_SYSTEM_STATUS: SystemStatus = {
  cpuTempC: null,
  ramUsagePercent: null,
  diskUsagePercent: null,
  pythonLoopFps: null,
  pythonLoopHealthy: false,
  pythonLoopLastTickMs: null,
  simulationMode: false,
  hardwareModeConfigured: 'auto',
  hardwareModeResolved: 'unknown',
  esp32Status: 'unknown',
  esp32Target: null,
  phoneBluetoothStatus: 'unknown',
  phoneBluetoothDeviceName: null,
  webClientCount: 0,
  useMicrophone: true,
  audioStreamHealthy: false,
  audioStreamState: 'unknown',
  lastAudioSampleAgeMs: null,
  dynamicAudioLatencyMs: null,
  uptimeSeconds: 0,
  hostname: 'unknown-host',
  platform: 'unknown',
  actions: {
    restartPython: { available: false, reason: null },
    rebootRaspberry: { available: false, reason: null },
    lastAction: null,
  },
};

type StatusDescriptor = {
  value: string;
  subtitle: string;
  color: string;
};

const formatOptional = (value: number | null, suffix: string, digits = 0) => {
  if (value === null || Number.isNaN(value)) {
    return '--';
  }
  return `${value.toFixed(digits)}${suffix}`;
};

const formatDuration = (seconds: number) => {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return '0M';
  }

  const totalSeconds = Math.floor(seconds);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);

  if (days > 0) return `${days}D ${hours}H`;
  if (hours > 0) return `${hours}H ${minutes}M`;
  return `${minutes}M`;
};

const describeSimulation = (system: SystemStatus): StatusDescriptor => {
  if (system.simulationMode) {
    return {
      value: 'SIMULATION',
      subtitle: `Configured: ${system.hardwareModeConfigured.toUpperCase()}`,
      color: '#63b3ed',
    };
  }

  return {
    value: 'RASPBERRY',
    subtitle: `Resolved: ${system.hardwareModeResolved.toUpperCase()}`,
    color: 'var(--lego-green)',
  };
};

const describeEsp32 = (system: SystemStatus): StatusDescriptor => {
  switch (system.esp32Status) {
    case 'simulation':
      return {
        value: 'SIMULATED',
        subtitle: system.esp32Target ? `Target ${system.esp32Target}` : 'Loopback output',
        color: '#63b3ed',
      };
    case 'reachable':
      return {
        value: 'ONLINE',
        subtitle: system.esp32Target ? `Target ${system.esp32Target}` : 'ESP32 reachable',
        color: 'var(--lego-green)',
      };
    case 'unreachable':
      return {
        value: 'OFFLINE',
        subtitle: system.esp32Target ? `No reply from ${system.esp32Target}` : 'No output target reply',
        color: 'var(--lego-red)',
      };
    case 'direct_gpio':
      return {
        value: 'DIRECT GPIO',
        subtitle: 'Current host drives LEDs directly',
        color: '#90cdf4',
      };
    default:
      return {
        value: 'UNKNOWN',
        subtitle: 'ESP32 reachability not available',
        color: 'var(--text-dim)',
      };
  }
};

const describePhone = (system: SystemStatus): StatusDescriptor => {
  if (system.phoneBluetoothStatus === 'connected') {
    return {
      value: 'CONNECTED',
      subtitle: system.phoneBluetoothDeviceName || 'Bluetooth device connected',
      color: 'var(--lego-green)',
    };
  }

  if (system.phoneBluetoothStatus === 'disconnected') {
    return {
      value: 'NOT CONNECTED',
      subtitle: 'No Bluetooth phone/audio device connected',
      color: 'var(--lego-orange)',
    };
  }

  return {
    value: 'UNKNOWN',
    subtitle: 'Bluetooth state not detectable on this host',
    color: 'var(--text-dim)',
  };
};

const describeAudio = (system: SystemStatus): StatusDescriptor => {
  if (!system.useMicrophone) {
    return {
      value: 'DISABLED',
      subtitle: 'Microphone capture disabled in config',
      color: 'var(--text-dim)',
    };
  }

  if (system.audioStreamState === 'error') {
    return {
      value: 'ERROR',
      subtitle: 'Audio stream failed to start or stay alive',
      color: 'var(--lego-red)',
    };
  }

  if (system.audioStreamState === 'running' && system.audioStreamHealthy) {
    return {
      value: 'RUNNING',
      subtitle: system.lastAudioSampleAgeMs !== null ? `${system.lastAudioSampleAgeMs} ms since sample` : 'Audio callback active',
      color: 'var(--lego-green)',
    };
  }

  if (system.audioStreamState === 'starting') {
    return {
      value: 'STARTING',
      subtitle: 'Waiting for the audio stream to warm up',
      color: 'var(--lego-orange)',
    };
  }

  return {
    value: String(system.audioStreamState || 'UNKNOWN').toUpperCase(),
    subtitle: 'Audio state is being detected',
    color: 'var(--text-dim)',
  };
};

const statusRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '10px',
  padding: '8px 10px',
  borderRadius: '8px',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.05)',
};

const StatusRow = ({ label, descriptor }: { label: string; descriptor: StatusDescriptor }) => (
  <div style={statusRowStyle}>
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', minWidth: 0 }}>
      <span style={{ color: 'var(--text-dim)', fontSize: '0.78rem', fontWeight: 800, letterSpacing: '0.08em' }}>{label}</span>
      <span style={{ color: '#e2e8f0', fontSize: '0.78rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '250px' }}>
        {descriptor.subtitle}
      </span>
    </div>
    <span className="digital-font" style={{ color: descriptor.color, fontSize: '1rem', textAlign: 'right', textShadow: `0 0 8px ${descriptor.color}` }}>
      {descriptor.value}
    </span>
  </div>
);

const ActionButton = ({
  label,
  variant,
  disabled,
  helper,
  onClick,
}: {
  label: string;
  variant: 'warning' | 'danger';
  disabled: boolean;
  helper: string;
  onClick: () => void;
}) => {
  const palette = variant === 'danger'
    ? {
        background: 'linear-gradient(180deg, #6f1111 0%, #451010 100%)',
        accent: '#ff9b2f',
        border: '#ff7a59',
        text: '#fff4f1',
        glow: 'rgba(255, 122, 89, 0.35)',
        stripe: 'repeating-linear-gradient(135deg, rgba(255,155,47,0.95), rgba(255,155,47,0.95) 7px, rgba(58,16,10,0.95) 7px, rgba(58,16,10,0.95) 14px)',
      }
    : {
        background: 'linear-gradient(180deg, #8f6b12 0%, #6e5107 100%)',
        accent: '#ffe082',
        border: '#f6d365',
        text: '#fffef5',
        glow: 'rgba(246, 211, 101, 0.28)',
        stripe: 'linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0))',
      };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: 'calc(11.2 * var(--stud))',
        minHeight: 'calc(2.35 * var(--stud))',
        cursor: disabled ? 'not-allowed' : 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '6px',
        padding: '7px 9px',
        borderRadius: '8px',
        border: `2px solid ${palette.border}`,
        background: palette.background,
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.14), 0 10px 18px rgba(0,0,0,0.45), 0 0 18px ${palette.glow}`,
        opacity: disabled ? 0.45 : 1,
        letterSpacing: '0.04em',
        position: 'relative',
        overflow: 'hidden',
        textAlign: 'left',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: palette.stripe,
          opacity: variant === 'danger' ? 0.18 : 0.32,
          pointerEvents: 'none',
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', position: 'relative', zIndex: 1 }}>
        <div
          style={{
            width: '24px',
            height: '24px',
            borderRadius: variant === 'danger' ? '8px' : '50%',
            background: `linear-gradient(180deg, ${palette.accent} 0%, rgba(255,255,255,0.18) 100%)`,
            color: variant === 'danger' ? '#4b100a' : '#362905',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 900,
            fontSize: '1rem',
            boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.55), inset 0 -2px 4px rgba(0,0,0,0.35)',
          }}
        >
          {variant === 'danger' ? '!' : 'R'}
        </div>
        <span style={{ color: palette.text, fontSize: '0.68rem', fontWeight: 900, textShadow: '0 1px 3px rgba(0,0,0,0.45)', letterSpacing: '0.02em' }}>
          {label}
        </span>
      </div>
      {variant === 'danger' ? (
        <span style={{ position: 'relative', zIndex: 1, color: '#ffd7c7', fontSize: '0.5rem', fontWeight: 900, letterSpacing: '0.08em' }}>
          DANGER
        </span>
      ) : null}
    </button>
    <span style={{ color: '#d7dde6', fontSize: '0.7rem', lineHeight: 1.28, minHeight: '1.8em' }}>{helper}</span>
  </div>
  );
};

export const SystemSetup = () => {
  const [system, setSystem] = useState<SystemStatus>(EMPTY_SYSTEM_STATUS);
  const bridgeStatus = useBridgeStatus();

  useEffect(() => {
    return subscribeModeMasterState((state) => {
      if (state.system) {
        setSystem(state.system);
      }
    });
  }, []);

  const loopColor = system.pythonLoopHealthy ? 'var(--lego-green)' : 'var(--lego-orange)';
  const loopSubtitle = system.pythonLoopLastTickMs !== null
    ? `${system.pythonLoopLastTickMs} ms since last tick`
    : 'Waiting for loop heartbeat';
  const latencySubtitle = system.dynamicAudioLatencyMs !== null
    ? `Latency ${system.dynamicAudioLatencyMs} ms`
    : system.platform;
  const lastAction = system.actions.lastAction;
  const lastActionColor =
    lastAction?.state === 'success'
      ? 'var(--lego-green)'
      : lastAction?.state === 'error'
        ? 'var(--lego-red)'
        : 'var(--lego-orange)';
  const canSendSystemAction = bridgeStatus === 'open';

  const confirmAndSend = (action: 'restart_python_loop' | 'restart_raspberry_pi') => {
    if (!canSendSystemAction) {
      return;
    }

    const confirmed = action === 'restart_python_loop'
      ? window.confirm('Restart the live Python loop now? The controller will briefly disconnect while it relaunches.')
      : window.confirm('Reboot the Raspberry Pi now? The show controller will disconnect and only return after the host finishes rebooting.');

    if (!confirmed) {
      return;
    }

    sendInstruction({ page: 'system', action });
  };

  return (
    <FitBoard width={BOARD_WIDTH} height={BOARD_HEIGHT}>
      <div style={{ position: 'relative', width: `${BOARD_WIDTH}px`, height: `${BOARD_HEIGHT}px` }}>
      {bridgeStatus !== 'open' ? (
        <div style={{ position: 'absolute', top: '60px', left: '108px', width: '420px', zIndex: 40 }}>
          <NoticeBanner tone={bridgeStatus === 'connecting' ? 'warning' : 'error'} title="SYSTEM CONTROL STATUS">
            {bridgeStatus === 'connecting'
              ? 'System controls will be available again once the bridge finishes reconnecting.'
              : 'System controls are disabled while the controller is offline.'}
          </NoticeBanner>
        </div>
      ) : null}
      <GridSpot col={6} row={0}>
        <div className="lego-label" style={{ width: 'calc(15 * var(--stud))' }}>SYSTEM & SETUP</div>
      </GridSpot>

      <GridSpot col={2} row={3}>
        <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(36)}px`, height: `${LEGO_MATH.physicalSize(23)}px` }}></div>
      </GridSpot>

      <GridSpot col={3} row={4}>
        <div className="lego-label" style={{ width: 'calc(18 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-green)' }}>LIVE TELEMETRY</div>
      </GridSpot>

      <GridSpot col={4} row={7}>
        <div className="embedded-oled" style={OLED_STYLE}>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 'bold' }}>CPU TEMP</span>
          <span className="digital-font" style={{ color: system.cpuTempC !== null ? 'var(--lego-orange)' : 'var(--text-dim)', fontSize: '1.9rem', textShadow: `0 0 10px ${system.cpuTempC !== null ? 'var(--lego-orange)' : 'rgba(255,255,255,0.15)'}`, marginTop: 'auto' }}>
            {formatOptional(system.cpuTempC, ' C', 1)}
          </span>
          <span style={{ color: '#9aa5b1', fontSize: '0.68rem', marginTop: '4px' }}>{system.hostname}</span>
        </div>
      </GridSpot>

      <GridSpot col={17} row={7}>
        <div className="embedded-oled" style={OLED_STYLE}>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 'bold' }}>PYTHON LOOP</span>
          <span className="digital-font" style={{ color: loopColor, fontSize: '1.85rem', textShadow: `0 0 10px ${loopColor}`, marginTop: 'auto' }}>
            {system.pythonLoopFps !== null ? `${system.pythonLoopFps.toFixed(1)} FPS` : 'WAITING'}
          </span>
          <span style={{ color: '#9aa5b1', fontSize: '0.68rem', marginTop: '4px' }}>{loopSubtitle}</span>
        </div>
      </GridSpot>

      <GridSpot col={4} row={13}>
        <div className="embedded-oled" style={OLED_STYLE}>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 'bold' }}>RAM / DISK</span>
          <span className="digital-font" style={{ color: '#90cdf4', fontSize: '1.75rem', textShadow: '0 0 10px #90cdf4', marginTop: 'auto' }}>
            {system.ramUsagePercent !== null ? `${system.ramUsagePercent.toFixed(1)}%` : '--'}
          </span>
          <span style={{ color: '#9aa5b1', fontSize: '0.68rem', marginTop: '4px' }}>
            {system.diskUsagePercent !== null ? `Disk ${system.diskUsagePercent.toFixed(1)}% used` : 'Disk usage unavailable'}
          </span>
        </div>
      </GridSpot>

      <GridSpot col={17} row={13}>
        <div className="embedded-oled" style={OLED_STYLE}>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontWeight: 'bold' }}>UPTIME / AUDIO</span>
          <span className="digital-font" style={{ color: '#f6e05e', fontSize: '1.75rem', textShadow: '0 0 10px #f6e05e', marginTop: 'auto' }}>
            {formatDuration(system.uptimeSeconds)}
          </span>
          <span style={{ color: '#9aa5b1', fontSize: '0.68rem', marginTop: '4px' }}>{latencySubtitle}</span>
        </div>
      </GridSpot>

      <GridSpot col={3} row={22}>
        <div style={{
          ...PANEL_INSET_STYLE,
          width: `${LEGO_MATH.physicalSize(28)}px`,
          minHeight: `${LEGO_MATH.physicalSize(7)}px`,
          transform: 'scale(1.2)',
          transformOrigin: 'top left',
        }}>
          <StatusRow label="MODE" descriptor={describeSimulation(system)} />
          <StatusRow label="ESP32 OUTPUT" descriptor={describeEsp32(system)} />
          <StatusRow label="PHONE TO PI" descriptor={describePhone(system)} />
          <StatusRow label="AUDIO INPUT" descriptor={describeAudio(system)} />
        </div>
      </GridSpot>

      <GridSpot col={39} row={4}>
        <div className="rogue-piece dark-grey" style={{ width: `${LEGO_MATH.physicalSize(13)}px`, height: `${LEGO_MATH.physicalSize(18)}px` }}></div>
      </GridSpot>

      <GridSpot col={40} row={5}>
        <div className="lego-label" style={{ width: 'calc(9.5 * var(--stud))', color: 'white', borderLeft: '5px solid var(--lego-red)' }}>CONTROL ROOM</div>
      </GridSpot>

      <GridSpot col={40} row={8}>
        <div style={{ ...PANEL_INSET_STYLE, width: `${LEGO_MATH.physicalSize(11)}px`, minHeight: `${LEGO_MATH.physicalSize(4.8)}px`, gap: '5px', padding: '7px 8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.68rem', fontWeight: 800 }}>WEB CLIENTS</span>
            <span className="digital-font" style={{ color: '#63b3ed', fontSize: '0.95rem', textShadow: '0 0 10px #63b3ed' }}>{system.webClientCount}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.68rem', fontWeight: 800 }}>HOST</span>
            <span style={{ color: '#e2e8f0', fontSize: '0.66rem', fontWeight: 700, maxWidth: '72px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {system.hostname}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.68rem', fontWeight: 800 }}>PLATFORM</span>
            <span style={{ color: '#e2e8f0', fontSize: '0.66rem', fontWeight: 700, maxWidth: '72px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {system.platform}
            </span>
          </div>
        </div>
      </GridSpot>

      <GridSpot col={40} row={13.5}>
        <div style={{ ...PANEL_INSET_STYLE, width: `${LEGO_MATH.physicalSize(11)}px`, minHeight: `${LEGO_MATH.physicalSize(4)}px`, gap: '4px', padding: '7px 8px' }}>
          <span style={{ color: 'var(--text-dim)', fontSize: '0.68rem', fontWeight: 800 }}>LAST ACTION</span>
          <span className="digital-font" style={{ color: lastAction ? lastActionColor : 'var(--text-dim)', fontSize: '0.92rem', textShadow: lastAction ? `0 0 8px ${lastActionColor}` : 'none' }}>
            {lastAction ? lastAction.state.toUpperCase() : 'IDLE'}
          </span>
          <span style={{ color: '#e2e8f0', fontSize: '0.62rem', lineHeight: 1.18 }}>
            {lastAction ? lastAction.message : 'No system action requested yet.'}
          </span>
        </div>
      </GridSpot>

      <GridSpot col={53} row={8}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <ActionButton
            label="RESTART PYTHON LOOP"
            variant="warning"
            disabled={!system.actions.restartPython.available || !canSendSystemAction}
            helper={
              !canSendSystemAction
                ? 'Requires a live controller connection.'
                : system.actions.restartPython.available
                  ? 'Self-restarts the running Python process after confirmation.'
                  : (system.actions.restartPython.reason || 'Restart is unavailable.')
            }
            onClick={() => confirmAndSend('restart_python_loop')}
          />
          <ActionButton
            label="REBOOT RASPBERRY PI"
            variant="danger"
            disabled={!system.actions.rebootRaspberry.available || !canSendSystemAction}
            helper={
              !canSendSystemAction
                ? 'Requires a live controller connection.'
                : system.actions.rebootRaspberry.available
                  ? 'Reboots the Raspberry after confirmation. The app should return after boot.'
                  : (system.actions.rebootRaspberry.reason || 'Reboot is unavailable.')
            }
            onClick={() => confirmAndSend('restart_raspberry_pi')}
          />
        </div>
      </GridSpot>
      </div>
    </FitBoard>
  );
};
