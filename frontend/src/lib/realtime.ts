/* Minimal realtime client SDK for Daily Set */

export type Envelope<T = any> = {
    v?: number;
    type: string;
    room?: string;
    from?: string;
    id?: string;
    ts?: string;
    payload?: T;
};

export type RealtimeOptions = {
    url: string; // ws(s)://host/ws
    token?: string; // bearer token for auth
    onMessage?: (e: Envelope) => void;
    onOpen?: () => void;
    onClose?: (ev: CloseEvent) => void;
    backoffBaseMs?: number;
};

export class RealtimeClient {
    private ws: WebSocket | null = null;
    private readonly opts: RealtimeOptions;
    private attempt = 0;
    private closed = false;

    constructor(opts: RealtimeOptions) {
        this.opts = opts;
    }

    connect() {
        this.closed = false;
        const url = new URL(this.opts.url);
        if (this.opts.token) {
            url.searchParams.set("token", this.opts.token);
        }
        this.ws = new WebSocket(url.toString());
        this.ws.onopen = () => {
            this.attempt = 0;
            this.opts.onOpen?.();
        };
        this.ws.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                this.opts.onMessage?.(data);
            } catch { }
        };
        this.ws.onclose = (ev) => {
            this.opts.onClose?.(ev);
            this.ws = null;
            if (!this.closed) {
                this.reconnect();
            }
        };
    }

    reconnect() {
        const base = this.opts.backoffBaseMs ?? 250;
        const delay = Math.min(10000, base * Math.pow(2, this.attempt++));
        setTimeout(() => this.connect(), delay + Math.floor(Math.random() * base));
    }

    close() {
        this.closed = true;
        this.ws?.close();
    }

    send(e: Envelope) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
        const env: Envelope = {
            v: 1,
            id: e.id || crypto.randomUUID?.() || `${Date.now()}`,
            ts: new Date().toISOString(),
            ...e,
        };
        this.ws.send(JSON.stringify(env));
        return true;
    }

    subscribe(room: string) {
        return this.send({ type: "subscribe", room });
    }

    action(room: string, payload: any) {
        return this.send({ type: "action", room, payload });
    }
}
