// Event sources for Replay and Live streams
import type { FixieEvent } from "./events";

export type EventSpeed = 1 | 2 | 4;

export interface EventSourceSubscriber {
  onEvent: (event: FixieEvent) => void;
  onError?: (err: Error) => void;
  onComplete?: () => void;
}

export interface FixieSource {
  subscribe(onEvent: (event: FixieEvent) => void, onError?: (err: Error) => void, onComplete?: () => void): () => void;
  pause(): void;
  resume(): void;
  setSpeed(speed: EventSpeed): void;
}

export class ReplaySource implements FixieSource {
  private runId: string;
  private baseUrl: string;
  private speed: EventSpeed = 1;
  private isPaused = false;
  private events: FixieEvent[] = [];
  private offsets: number[] = [];
  private currentIndex = 0;
  private virtualElapsed = 0;
  private lastAnchorReal = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private subscribers = new Set<EventSourceSubscriber>();
  private loaded = false;
  private isAborted = false;

  constructor(runId: string, options?: { baseUrl?: string; initialSpeed?: EventSpeed; rawEvents?: FixieEvent[] }) {
    this.runId = runId;
    this.baseUrl = options?.baseUrl ?? "";
    if (options?.initialSpeed) this.speed = options.initialSpeed;
    if (options?.rawEvents) this.initEvents(options.rawEvents);
  }

  private initEvents(events: FixieEvent[]) {
    this.events = events;
    const baseTime = this.events.length > 0 ? new Date(this.events[0].ts).getTime() : 0;
    this.offsets = this.events.map((e) => {
      const t = new Date(e.ts).getTime();
      return isNaN(t) || isNaN(baseTime) ? 0 : Math.max(0, t - baseTime);
    });
    this.loaded = true;
  }

  private getVirtualTime(): number {
    if (this.isPaused || this.lastAnchorReal === 0) return this.virtualElapsed;
    return this.virtualElapsed + (Date.now() - this.lastAnchorReal) * this.speed;
  }

  private scheduleNext() {
    if (this.isPaused || this.isAborted || this.currentIndex >= this.events.length) return;
    const delta = this.offsets[this.currentIndex] - this.getVirtualTime();
    if (delta <= 0) {
      this.emitCurrentAndAdvance();
    } else {
      this.timer = setTimeout(() => this.emitCurrentAndAdvance(), Math.max(0, delta / this.speed));
    }
  }

  private emitCurrentAndAdvance() {
    if (this.isPaused || this.isAborted || this.currentIndex >= this.events.length) return;
    const ev = this.events[this.currentIndex];
    this.virtualElapsed = Math.max(this.virtualElapsed, this.offsets[this.currentIndex]);
    this.lastAnchorReal = Date.now();
    this.currentIndex++;

    for (const sub of this.subscribers) {
      try { sub.onEvent(ev); } catch (err) { sub.onError?.(err instanceof Error ? err : new Error(String(err))); }
    }
    if (this.currentIndex >= this.events.length) {
      for (const sub of this.subscribers) sub.onComplete?.();
    } else {
      this.scheduleNext();
    }
  }

  subscribe(onEvent: (event: FixieEvent) => void, onError?: (err: Error) => void, onComplete?: () => void): () => void {
    const sub: EventSourceSubscriber = { onEvent, onError, onComplete };
    this.subscribers.add(sub);
    this.isAborted = false;

    if (!this.loaded) {
      const filename = this.runId.endsWith(".jsonl") ? this.runId : `${this.runId}.jsonl`;
      fetch(`${this.baseUrl}/replays/${filename}`)
        .then(async (res) => {
          if (!res.ok) throw new Error(`Replay fetch failed with status ${res.status}`);
          const text = await res.text();
          const parsed = text.split("\n").filter((l) => l.trim().length > 0).map((l) => JSON.parse(l) as FixieEvent);
          this.initEvents(parsed);
          this.lastAnchorReal = Date.now();
          this.scheduleNext();
        })
        .catch((err) => sub.onError?.(err instanceof Error ? err : new Error(String(err))));
    } else if (this.currentIndex < this.events.length && !this.isPaused) {
      this.lastAnchorReal = Date.now();
      this.scheduleNext();
    }

    return () => {
      this.subscribers.delete(sub);
      if (this.subscribers.size === 0) {
        this.isAborted = true;
        if (this.timer) { clearTimeout(this.timer); this.timer = null; }
      }
    };
  }

  pause() {
    if (this.isPaused) return;
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    this.virtualElapsed = this.getVirtualTime();
    this.isPaused = true;
  }

  resume() {
    if (!this.isPaused) return;
    this.isPaused = false;
    this.lastAnchorReal = Date.now();
    this.scheduleNext();
  }

  setSpeed(speed: EventSpeed) {
    if (speed === this.speed) return;
    if (!this.isPaused) {
      if (this.timer) { clearTimeout(this.timer); this.timer = null; }
      this.virtualElapsed = this.getVirtualTime();
      this.lastAnchorReal = Date.now();
      this.speed = speed;
      this.scheduleNext();
    } else {
      this.speed = speed;
    }
  }
}

export class LiveSource implements FixieSource {
  private runId: string;
  private apiUrl: string;
  private isPaused = false;
  private speed: EventSpeed = 1;
  private buffer: FixieEvent[] = [];
  private subscribers = new Set<EventSourceSubscriber>();
  private es: EventSource | null = null;
  private lastEventId: string | null = null;
  private errorGraceTimer: ReturnType<typeof setTimeout> | null = null;
  private isClosed = false;

  constructor(runId: string, options?: { apiUrl?: string }) {
    this.runId = runId;
    this.apiUrl = (options?.apiUrl ?? process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
  }

  private emit(event: FixieEvent) {
    for (const sub of this.subscribers) sub.onEvent(event);
  }

  private complete() {
    if (this.isClosed) return;
    this.isClosed = true;
    this.close();
    for (const sub of this.subscribers) sub.onComplete?.();
  }

  private fail(err: Error) {
    for (const sub of this.subscribers) sub.onError?.(err);
  }

  private close() {
    if (this.errorGraceTimer) { clearTimeout(this.errorGraceTimer); this.errorGraceTimer = null; }
    if (this.es) { this.es.close(); this.es = null; }
  }

  subscribe(onEvent: (event: FixieEvent) => void, onError?: (err: Error) => void, onComplete?: () => void): () => void {
    const sub: EventSourceSubscriber = { onEvent, onError, onComplete };
    this.subscribers.add(sub);
    if (!this.apiUrl) {
      sub.onError?.(new Error("Live source unavailable: NEXT_PUBLIC_API_URL is not set"));
      return () => this.subscribers.delete(sub);
    }

    fetch(`${this.apiUrl}/health`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Health check failed with status ${res.status}`);
        const data = await res.json();
        if (!data.live_enabled) throw new Error("Live source unavailable: live_enabled is false");
        this.connect();
      })
      .catch((err) => this.fail(err instanceof Error ? err : new Error(String(err))));

    return () => {
      this.subscribers.delete(sub);
      if (this.subscribers.size === 0) this.close();
    };
  }

  private connect() {
    if (this.isClosed || typeof EventSource === "undefined") return;
    const url = new URL(`${this.apiUrl}/runs/${this.runId}/events`);
    if (this.lastEventId) url.searchParams.set("last_event_id", this.lastEventId);

    const es = new EventSource(url.toString());
    this.es = es;

    es.onmessage = (msg: MessageEvent) => {
      if (msg.lastEventId) this.lastEventId = msg.lastEventId;
      try {
        const ev = JSON.parse(msg.data) as FixieEvent;
        if (ev.seq !== undefined && !this.lastEventId) this.lastEventId = String(ev.seq);
        if (this.isPaused) { this.buffer.push(ev); } else { this.emit(ev); }

        if (ev.type === "run.error") {
          if (!this.errorGraceTimer) this.errorGraceTimer = setTimeout(() => this.complete(), 3000);
        } else if (ev.type === "run.finished") {
          if (this.errorGraceTimer) { clearTimeout(this.errorGraceTimer); this.errorGraceTimer = null; }
          this.complete();
        }
      } catch (err) {
        this.fail(err instanceof Error ? err : new Error(String(err)));
      }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) this.fail(new Error("EventSource connection closed"));
    };
  }

  pause() { this.isPaused = true; }

  resume() {
    if (!this.isPaused) return;
    this.isPaused = false;
    while (this.buffer.length > 0) {
      const ev = this.buffer.shift();
      if (ev) this.emit(ev);
    }
  }

  setSpeed(speed: EventSpeed) { this.speed = speed; }
}
