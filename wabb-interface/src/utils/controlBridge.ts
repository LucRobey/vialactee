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
  playlists: string[];
  availableModes: string[];
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

const isModeMasterSegmentState = (value: unknown): value is ModeMasterSegmentState => (
  isRecord(value)
  && typeof value.id === 'string'
  && typeof value.name === 'string'
  && typeof value.mode === 'string'
  && (value.direction === 'UP' || value.direction === 'DOWN')
  && typeof value.blocked === 'boolean'
  && (typeof value.targetMode === 'string' || value.targetMode === null)
  && typeof value.inTransition === 'boolean'
);

const isModeSettingDescriptor = (value: unknown): value is ModeSettingDescriptor => (
  isRecord(value)
  && typeof value.key === 'string'
  && typeof value.label === 'string'
  && (value.control === 'switch' || value.control === 'slider' || value.control === 'list')
  && (value.valueType === 'boolean' || value.valueType === 'number' || value.valueType === 'string')
);

const isModeSettingsCatalogEntry = (value: unknown): value is ModeSettingsCatalogEntry => (
  isRecord(value)
  && typeof value.mode === 'string'
  && typeof value.label === 'string'
  && Array.isArray(value.settings)
  && value.settings.every(isModeSettingDescriptor)
);

const isSystemActionCapability = (value: unknown): value is SystemActionCapability => (
  isRecord(value)
  && typeof value.available === 'boolean'
  && (typeof value.reason === 'string' || value.reason === null)
);

const isSystemActionFeedback = (value: unknown): value is SystemActionFeedback => (
  isRecord(value)
  && typeof value.action === 'string'
  && (value.state === 'pending' || value.state === 'success' || value.state === 'error')
  && typeof value.message === 'string'
  && typeof value.timestampMs === 'number'
);

const isSystemStatus = (value: unknown): value is SystemStatus => (
  isRecord(value)
  && typeof value.pythonLoopHealthy === 'boolean'
  && typeof value.simulationMode === 'boolean'
  && typeof value.hardwareModeConfigured === 'string'
  && typeof value.hardwareModeResolved === 'string'
  && typeof value.webClientCount === 'number'
  && typeof value.useMicrophone === 'boolean'
  && typeof value.audioStreamHealthy === 'boolean'
  && typeof value.audioStreamState === 'string'
  && typeof value.uptimeSeconds === 'number'
  && typeof value.hostname === 'string'
  && typeof value.platform === 'string'
  && isRecord(value.actions)
  && isSystemActionCapability(value.actions.restartPython)
  && isSystemActionCapability(value.actions.rebootRaspberry)
  && (value.actions.lastAction === null || isSystemActionFeedback(value.actions.lastAction))
);

const isModeMasterState = (value: unknown): value is ModeMasterState => (
  isRecord(value)
  && (typeof value.activePlaylist === 'string' || value.activePlaylist === null)
  && Array.isArray(value.enabledPlaylists)
  && value.enabledPlaylists.every(item => typeof item === 'string')
  && (typeof value.activeConfiguration === 'string' || value.activeConfiguration === null)
  && (typeof value.queuedConfiguration === 'string' || value.queuedConfiguration === null)
  && typeof value.selectedTransition === 'string'
  && typeof value.transitionLocked === 'boolean'
  && (typeof value.transitionState === 'string' || value.transitionState === null)
  && typeof value.transitionProgress === 'number'
  && typeof value.luminosity === 'number'
  && typeof value.sensibility === 'number'
  && Array.isArray(value.playlists)
  && value.playlists.every(item => typeof item === 'string')
  && Array.isArray(value.availableModes)
  && value.availableModes.every(item => typeof item === 'string')
  && Array.isArray(value.segments)
  && value.segments.every(isModeMasterSegmentState)
  && Array.isArray(value.modeSettingsCatalog)
  && value.modeSettingsCatalog.every(isModeSettingsCatalogEntry)
  && isRecord(value.modeSettings)
  && isSystemStatus(value.system)
);

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

      if (!isModeMasterState(message.payload)) {
        console.warn('Invalid mode master state payload received from websocket');
        return;
      }

      const state = message.payload;
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
