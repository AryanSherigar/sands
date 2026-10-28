// A recording stand-in for the Web Audio surface the ambient controller and the
// cue engine use, so timing and gain automation can be asserted without sound.

interface GainCall {
  kind: "set" | "linear" | "exp" | "cancel";
  value: number;
  time: number;
}

class FakeGainParam {
  value = 0;
  calls: GainCall[] = [];
  setValueAtTime(value: number, time: number): void {
    this.value = value;
    this.calls.push({ kind: "set", value, time });
  }
  linearRampToValueAtTime(value: number, time: number): void {
    this.calls.push({ kind: "linear", value, time });
  }
  exponentialRampToValueAtTime(value: number, time: number): void {
    this.calls.push({ kind: "exp", value, time });
  }
  cancelScheduledValues(time: number): void {
    this.calls.push({ kind: "cancel", value: 0, time });
  }
}

export class FakeGainNode {
  gain = new FakeGainParam();
  connections: unknown[] = [];
  connect(target: unknown): void {
    this.connections.push(target);
  }
}

export class FakeBufferSource {
  buffer: FakeAudioBuffer | null = null;
  onended: (() => void) | null = null;
  hasStarted = false;
  connections: unknown[] = [];
  connect(target: unknown): void {
    this.connections.push(target);
  }
  start(): void {
    this.hasStarted = true;
  }
  finish(): void {
    this.onended?.();
  }
}

export class FakeAudioBuffer {
  private readonly channel: Float32Array;
  constructor(
    readonly numberOfChannels: number,
    readonly length: number,
    readonly sampleRate: number,
  ) {
    this.channel = new Float32Array(length);
  }
  get duration(): number {
    return this.length / this.sampleRate;
  }
  getChannelData(): Float32Array {
    return this.channel;
  }
}

export class FakeAudioContext {
  static instances: FakeAudioContext[] = [];
  currentTime = 0;
  state: "running" | "suspended" = "running";
  sampleRate = 8000;
  destination = { kind: "destination" };
  gains: FakeGainNode[] = [];
  sources: FakeBufferSource[] = [];

  constructor() {
    FakeAudioContext.instances.push(this);
  }
  createGain(): FakeGainNode {
    const node = new FakeGainNode();
    this.gains.push(node);
    return node;
  }
  createMediaElementSource() {
    return { connect() {} };
  }
  createBuffer(channels: number, length: number, rate: number): FakeAudioBuffer {
    return new FakeAudioBuffer(channels, length, rate);
  }
  createBufferSource(): FakeBufferSource {
    const source = new FakeBufferSource();
    this.sources.push(source);
    return source;
  }
  resume(): Promise<void> {
    this.state = "running";
    return Promise.resolve();
  }
}
