export type WabbInstruction = {
  page: 'live_deck' | 'topology' | 'auto_dj' | 'system';
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
  segments: ModeMasterSegmentState[];
};

type SocketStatus = 'idle' | 'connecting' | 'open' | 'closed';
type StateListener = (state: ModeMasterState) => void;

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
  private readonly queue: string[] = [];
  private readonly url = buildBridgeUrl();
  private readonly stateListeners = new Set<StateListener>();
  private latestState: ModeMasterState | null = null;

  private connect() {
    if (this.status === 'open' || this.status === 'connecting') {
      return;
    }

    this.status = 'connecting';
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.status = 'open';
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
      this.status = 'closed';
      this.socket = null;
      this.scheduleReconnect();
    };

    this.socket.onerror = () => {
      this.status = 'closed';
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.reconnectTimer !== null) {
      return;
    }

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 1500);
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

      const state = message.payload as ModeMasterState;
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
}

const bridge = new ControlBridge();

export const sendInstruction = (instruction: Omit<WabbInstruction, 'timestamp'>) => {
  bridge.send(instruction);
};

export const subscribeModeMasterState = (listener: StateListener) => {
  return bridge.subscribeState(listener);
};
