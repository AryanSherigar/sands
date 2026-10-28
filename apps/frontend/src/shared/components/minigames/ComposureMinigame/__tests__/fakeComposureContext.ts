// A recording Web Audio stand-in for the synthesis in composureAudio.ts.

class FakeParam {
  value = 0;
  calls: Array<{ kind: string; value: number; time: number }> = [];
  setValueAtTime(value: number, time: number): void {
    this.value = value;
    this.calls.push({ kind: "set", value, time });
  }
  exponentialRampToValueAtTime(value: number, time: number): void {
    this.calls.push({ kind: "exp", value, time });
  }
}

export class FakeNode {
  gain = new FakeParam();
  frequency = new FakeParam();
  pan = new FakeParam();
  type = "";
  buffer: unknown = null;
  startedAt: number | null = null;
  stoppedAt: number | null = null;
  connections: unknown[] = [];
  connect(target: unknown): void {
    this.connections.push(target);
  }
  start(at: number): void {
    this.startedAt = at;
  }
  stop(at: number): void {
    this.stoppedAt = at;
  }
}

export class FakeComposureContext {
  currentTime = 0;
  sampleRate = 1000;
  state: "running" | "suspended" = "running";
  destination = { kind: "destination" };
  oscillators: FakeNode[] = [];
  sources: FakeNode[] = [];
  gains: FakeNode[] = [];
  panners: FakeNode[] = [];
  closed = false;
  createGain(): FakeNode {
    const node = new FakeNode();
    this.gains.push(node);
    return node;
  }
  createOscillator(): FakeNode {
    const node = new FakeNode();
    this.oscillators.push(node);
    return node;
  }
  createBufferSource(): FakeNode {
    const node = new FakeNode();
    this.sources.push(node);
    return node;
  }
  createStereoPanner(): FakeNode {
    const node = new FakeNode();
    this.panners.push(node);
    return node;
  }
  createBuffer(_channels: number, length: number) {
    const data = new Float32Array(length);
    return { getChannelData: () => data, length };
  }
  suspend(): Promise<void> {
    this.state = "suspended";
    return Promise.resolve();
  }
  resume(): Promise<void> {
    this.state = "running";
    return Promise.resolve();
  }
  close(): Promise<void> {
    this.closed = true;
    return Promise.resolve();
  }
}
