export type ModeSettingValue = string | number | boolean;

export type ModeSettingOption = {
  label: string;
  value: ModeSettingValue;
};

export type ModeSettingDescriptor = {
  key: string;
  label: string;
  control: 'switch' | 'slider' | 'list';
  valueType: 'boolean' | 'number' | 'string';
  default: ModeSettingValue;
  min?: number;
  max?: number;
  step?: number;
  integer?: boolean;
  unit?: string;
  options?: ModeSettingOption[];
};

export type ModeSettingsCatalogEntry = {
  mode: string;
  label: string;
  settings: ModeSettingDescriptor[];
};

export type WabbInstruction = {
  page: 'live_deck' | 'topology' | 'mode_settings' | 'system';
  action: string;
  payload?: Record<string, unknown>;
  timestamp: number;
};

export type ModeMasterSegmentState = {
  id: string;
  name: string;
  mode: string;
  direction: 'UP' | 'DOWN';
  blocked: boolean;
  targetMode: string | null;
  inTransition: boolean;
};

export type SystemActionCapability = {
  available: boolean;
  reason: string | null;
};

export type SystemActionFeedback = {
  action: string;
  state: 'pending' | 'success' | 'error';
  message: string;
  timestampMs: number;
};

export type SystemStatus = {
  cpuTempC: number | null;
  ramUsagePercent: number | null;
  diskUsagePercent: number | null;
  pythonLoopFps: number | null;
  pythonLoopHealthy: boolean;
  pythonLoopLastTickMs: number | null;
  simulationMode: boolean;
  hardwareModeConfigured: string;
  hardwareModeResolved: string;
  esp32Status: 'simulation' | 'reachable' | 'unreachable' | 'direct_gpio' | 'unknown';
  esp32Target: string | null;
  phoneBluetoothStatus: 'connected' | 'disconnected' | 'unknown';
  phoneBluetoothDeviceName: string | null;
  webClientCount: number;
  useMicrophone: boolean;
  audioStreamHealthy: boolean;
  audioStreamState: string;
  lastAudioSampleAgeMs: number | null;
  dynamicAudioLatencyMs: number | null;
  uptimeSeconds: number;
  hostname: string;
  platform: string;
  actions: {
    restartPython: SystemActionCapability;
    rebootRaspberry: SystemActionCapability;
    lastAction: SystemActionFeedback | null;
  };
};

export type ModeMasterState = {
  hardwareProfile?: string;
  activePlaylist: string | null;
  enabledPlaylists: string[];
  activeConfiguration: string | null;
  queuedConfiguration: string | null;
  selectedTransition: string;
  transitionLocked: boolean;
  transitionState: string | null;
  transitionProgress: number;
  luminosity: number;
  sensibility: number;
  autoTransitionTime: number;
  playlists: string[];
  availableModes: string[];
  activeMood?: string | null;
  availableMoods?: string[];
  segments: ModeMasterSegmentState[];
  modeSettingsCatalog: ModeSettingsCatalogEntry[];
  modeSettings: Record<string, Record<string, ModeSettingValue>>;
  system: SystemStatus;
};

export type SocketStatus = 'idle' | 'connecting' | 'open' | 'closed';
type StateListener = (state: ModeMasterState) => void;
type StatusListener = (status: SocketStatus) => void;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

export const normalizeModeMasterState = (value: unknown): ModeMasterState | null => {
  if (!isRecord(value)) {
    return null;
  }

  const systemRaw = isRecord(value.system) ? value.system : {};
  const actionsRaw = isRecord(systemRaw.actions) ? systemRaw.actions : {};
  const restartPythonRaw = isRecord(actionsRaw.restartPython) ? actionsRaw.restartPython : {};
  const rebootRaspberryRaw = isRecord(actionsRaw.rebootRaspberry) ? actionsRaw.rebootRaspberry : {};
  const lastActionRaw = isRecord(actionsRaw.lastAction) ? actionsRaw.lastAction : null;

  const system: SystemStatus = {
    cpuTempC: typeof systemRaw.cpuTempC === 'number' ? systemRaw.cpuTempC : null,
    ramUsagePercent: typeof systemRaw.ramUsagePercent === 'number' ? systemRaw.ramUsagePercent : null,
    diskUsagePercent: typeof systemRaw.diskUsagePercent === 'number' ? systemRaw.diskUsagePercent : null,
    pythonLoopFps: typeof systemRaw.pythonLoopFps === 'number' ? systemRaw.pythonLoopFps : null,
    pythonLoopHealthy: Boolean(systemRaw.pythonLoopHealthy),
    pythonLoopLastTickMs: typeof systemRaw.pythonLoopLastTickMs === 'number' ? systemRaw.pythonLoopLastTickMs : null,
    simulationMode: Boolean(systemRaw.simulationMode),
    hardwareModeConfigured: typeof systemRaw.hardwareModeConfigured === 'string' ? systemRaw.hardwareModeConfigured : 'auto',
    hardwareModeResolved: typeof systemRaw.hardwareModeResolved === 'string' ? systemRaw.hardwareModeResolved : 'unknown',
    esp32Status: (['simulation', 'reachable', 'unreachable', 'direct_gpio', 'unknown'].includes(systemRaw.esp32Status as string)
      ? systemRaw.esp32Status
      : 'unknown') as SystemStatus['esp32Status'],
    esp32Target: typeof systemRaw.esp32Target === 'string' ? systemRaw.esp32Target : null,
    phoneBluetoothStatus: (['connected', 'disconnected', 'unknown'].includes(systemRaw.phoneBluetoothStatus as string)
      ? systemRaw.phoneBluetoothStatus
      : 'unknown') as SystemStatus['phoneBluetoothStatus'],
    phoneBluetoothDeviceName: typeof systemRaw.phoneBluetoothDeviceName === 'string' ? systemRaw.phoneBluetoothDeviceName : null,
    webClientCount: typeof systemRaw.webClientCount === 'number' ? systemRaw.webClientCount : 0,
    useMicrophone: systemRaw.useMicrophone !== false,
    audioStreamHealthy: Boolean(systemRaw.audioStreamHealthy),
    audioStreamState: typeof systemRaw.audioStreamState === 'string' ? systemRaw.audioStreamState : 'unknown',
    lastAudioSampleAgeMs: typeof systemRaw.lastAudioSampleAgeMs === 'number' ? systemRaw.lastAudioSampleAgeMs : null,
    dynamicAudioLatencyMs: typeof systemRaw.dynamicAudioLatencyMs === 'number' ? systemRaw.dynamicAudioLatencyMs : null,
    uptimeSeconds: typeof systemRaw.uptimeSeconds === 'number' ? systemRaw.uptimeSeconds : 0,
    hostname: typeof systemRaw.hostname === 'string' ? systemRaw.hostname : 'unknown-host',
    platform: typeof systemRaw.platform === 'string' ? systemRaw.platform : 'unknown',
    actions: {
      restartPython: {
        available: Boolean(restartPythonRaw.available),
        reason: typeof restartPythonRaw.reason === 'string' ? restartPythonRaw.reason : null,
      },
      rebootRaspberry: {
        available: Boolean(rebootRaspberryRaw.available),
        reason: typeof rebootRaspberryRaw.reason === 'string' ? rebootRaspberryRaw.reason : null,
      },
      lastAction: lastActionRaw && typeof lastActionRaw.action === 'string'
        ? {
            action: lastActionRaw.action,
            state: (['pending', 'success', 'error'].includes(lastActionRaw.state as string) ? lastActionRaw.state : 'pending') as SystemActionFeedback['state'],
            message: typeof lastActionRaw.message === 'string' ? lastActionRaw.message : '',
            timestampMs: typeof lastActionRaw.timestampMs === 'number' ? lastActionRaw.timestampMs : Date.now(),
          }
        : null,
    },
  };

  const segments: ModeMasterSegmentState[] = Array.isArray(value.segments)
    ? value.segments.filter(isRecord).map(seg => ({
        id: String(seg.id ?? ''),
        name: String(seg.name ?? ''),
        mode: String(seg.mode ?? 'Rainbow'),
        direction: (seg.direction === 'DOWN' ? 'DOWN' : 'UP') as 'UP' | 'DOWN',
        blocked: Boolean(seg.blocked),
        targetMode: typeof seg.targetMode === 'string' ? seg.targetMode : null,
        inTransition: Boolean(seg.inTransition),
      }))
    : [];

  const catalog: ModeSettingsCatalogEntry[] = Array.isArray(value.modeSettingsCatalog)
    ? value.modeSettingsCatalog.filter(isRecord).map(cat => ({
        mode: String(cat.mode ?? ''),
        label: String(cat.label ?? ''),
        settings: Array.isArray(cat.settings)
          ? cat.settings.filter(isRecord).map(s => ({
              key: String(s.key ?? ''),
              label: String(s.label ?? ''),
              control: (['switch', 'slider', 'list'].includes(s.control as string) ? s.control : 'slider') as ModeSettingDescriptor['control'],
              valueType: (['boolean', 'number', 'string'].includes(s.valueType as string) ? s.valueType : 'number') as ModeSettingDescriptor['valueType'],
              default: (s.default ?? 0) as ModeSettingValue,
              min: typeof s.min === 'number' ? s.min : undefined,
              max: typeof s.max === 'number' ? s.max : undefined,
              step: typeof s.step === 'number' ? s.step : undefined,
              integer: typeof s.integer === 'boolean' ? s.integer : undefined,
              unit: typeof s.unit === 'string' ? s.unit : undefined,
              options: Array.isArray(s.options)
                ? s.options.filter(isRecord).map(opt => ({
                    label: String(opt.label ?? ''),
                    value: (opt.value ?? '') as ModeSettingValue,
                  }))
                : undefined,
            }))
          : [],
      }))
    : [];

  const modeSettings: Record<string, Record<string, ModeSettingValue>> = {};
  if (isRecord(value.modeSettings)) {
    Object.entries(value.modeSettings).forEach(([m, s]) => {
      if (isRecord(s)) {
        modeSettings[m] = { ...s } as Record<string, ModeSettingValue>;
      }
    });
  }

  return {
    hardwareProfile: typeof value.hardwareProfile === 'string' ? value.hardwareProfile : undefined,
    activePlaylist: typeof value.activePlaylist === 'string' ? value.activePlaylist : null,
    enabledPlaylists: Array.isArray(value.enabledPlaylists) ? value.enabledPlaylists.filter((p): p is string => typeof p === 'string') : [],
    activeConfiguration: typeof value.activeConfiguration === 'string' ? value.activeConfiguration : null,
    queuedConfiguration: typeof value.queuedConfiguration === 'string' ? value.queuedConfiguration : null,
    selectedTransition: typeof value.selectedTransition === 'string' ? value.selectedTransition : 'CUT',
    transitionLocked: Boolean(value.transitionLocked),
    transitionState: typeof value.transitionState === 'string' ? value.transitionState : null,
    transitionProgress: typeof value.transitionProgress === 'number' ? value.transitionProgress : 0,
    luminosity: typeof value.luminosity === 'number' ? value.luminosity : 60,
    sensibility: typeof value.sensibility === 'number' ? value.sensibility : 70,
    autoTransitionTime: typeof value.autoTransitionTime === 'number' ? value.autoTransitionTime : 20,
    playlists: Array.isArray(value.playlists) ? value.playlists.filter((p): p is string => typeof p === 'string') : [],
    availableModes: Array.isArray(value.availableModes) ? value.availableModes.filter((m): m is string => typeof m === 'string') : [],
    activeMood: typeof value.activeMood === 'string' ? value.activeMood : null,
    availableMoods: Array.isArray(value.availableMoods) ? value.availableMoods.filter((m): m is string => typeof m === 'string') : [],
    segments,
    modeSettingsCatalog: catalog,
    modeSettings,
    system,
  };
};

const buildBridgeUrl = () => {
  const envUrl = import.meta.env.VITE_WABB_WS_URL;
  if (typeof envUrl === 'string' && envUrl.length > 0) {
    return envUrl;
  }

  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.hostname}:8080/ws`;
};

class ControlBridge {
  private socket: WebSocket | null = null;
  private status: SocketStatus = 'idle';
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private readonly queue: string[] = [];
  private readonly url = buildBridgeUrl();
  private readonly stateListeners = new Set<StateListener>();
  private readonly statusListeners = new Set<StatusListener>();
  private latestState: ModeMasterState | null = null;

  private setStatus(status: SocketStatus) {
    if (this.status === status) {
      return;
    }

    this.status = status;
    this.statusListeners.forEach(listener => listener(status));
  }

  private connect() {
    if (this.status === 'open' || this.status === 'connecting') {
      return;
    }

    this.setStatus('connecting');
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus('open');
      while (this.queue.length > 0) {
        const message = this.queue.shift();
        if (!message) break;
        this.socket?.send(message);
      }
    };

    this.socket.onmessage = (event) => {
      this.handleMessage(event.data);
    };

    this.socket.onclose = () => {
      this.socket = null;
      this.setStatus('closed');
      this.scheduleReconnect();
    };

    this.socket.onerror = () => {
      this.socket = null;
      this.setStatus('closed');
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer !== null) {
      return;
    }

    const delayMs = Math.min(1000 * (2 ** this.reconnectAttempts), 30000);
    this.reconnectAttempts += 1;

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delayMs);
  }

  private handleMessage(rawMessage: unknown) {
    if (typeof rawMessage !== 'string') {
      return;
    }

    try {
      const message = JSON.parse(rawMessage) as { type?: unknown; payload?: unknown };
      if (message.type !== 'mode_master_state' || !message.payload) {
        return;
      }

      const state = normalizeModeMasterState(message.payload);
      if (!state) {
        console.warn('Invalid mode master state payload received from websocket');
        return;
      }

      this.latestState = state;
      this.stateListeners.forEach(listener => listener(state));
    } catch (error) {
      console.warn('Invalid websocket message from mode master', error);
    }
  }

  send(instruction: Omit<WabbInstruction, 'timestamp'>) {
    const event: WabbInstruction = { ...instruction, timestamp: Date.now() };
    const payload = JSON.stringify(event);

    if (this.status !== 'open') {
      this.queue.push(payload);
      this.connect();
      return;
    }

    this.socket?.send(payload);
  }

  subscribeState(listener: StateListener) {
    this.stateListeners.add(listener);
    if (this.latestState) {
      listener(this.latestState);
    }
    this.connect();

    return () => {
      this.stateListeners.delete(listener);
    };
  }

  subscribeStatus(listener: StatusListener) {
    this.statusListeners.add(listener);
    listener(this.status);
    this.connect();

    return () => {
      this.statusListeners.delete(listener);
    };
  }

  getStatus() {
    return this.status;
  }
}

const bridge = new ControlBridge();

export const sendInstruction = (instruction: Omit<WabbInstruction, 'timestamp'>) => {
  bridge.send(instruction);
};

export const subscribeModeMasterState = (listener: StateListener) => {
  return bridge.subscribeState(listener);
};

export const subscribeBridgeStatus = (listener: StatusListener) => {
  return bridge.subscribeStatus(listener);
};

export const getBridgeStatus = () => bridge.getStatus();
