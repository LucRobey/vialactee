export type WabbInstruction = {
  page: 'live_deck' | 'topology' | 'auto_dj' | 'system';
  action: string;
  payload?: Record<string, unknown>;
  timestamp: number;
};

type SocketStatus = 'idle' | 'connecting' | 'open' | 'closed';

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

    this.socket.onclose = () => {
      this.status = 'closed';
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
}

const bridge = new ControlBridge();

export const sendInstruction = (instruction: Omit<WabbInstruction, 'timestamp'>) => {
  bridge.send(instruction);
};
