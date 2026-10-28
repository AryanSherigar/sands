import { WELCOME_ASSET_ROOT, WELCOME_BODY_SECONDS, WELCOME_HOLD_SECONDS, WELCOME_BLACK_SECONDS } from "../constants/welcomeTape";

export class WelcomePlayback {
  readonly context = new AudioContext();
  readonly gain = this.context.createGain();
  readonly analyser = this.context.createAnalyser();
  private buffers: AudioBuffer[] = [];
  private sources: AudioBufferSourceNode[] = [];
  private startedAt = 0;
  private elapsed = 0;
  private isPlaying = false;
  private urls: string[] = [];
  private isDisposed = false;
  constructor() { this.gain.connect(this.context.destination); this.analyser.connect(this.gain); }
  async load(signal: AbortSignal): Promise<string[]> {
    const names = ["body.wav", "closing.wav", "ambience.wav"];
    this.buffers = await Promise.all(names.map(async name =>
      this.context.decodeAudioData(await this.fetchAsset(name, signal))));
    const pictures = ["acquisition.mp4", "body.mp4", "katie.png", "expression.png"];
    return Promise.all(pictures.map(async name => {
      const bytes = await this.fetchAsset(name, signal);
      if (this.isDisposed || signal.aborted) throw new Error("Tape closed");
      const mime = name.endsWith("png") ? "image/png" : "video/mp4";
      const url = URL.createObjectURL(new Blob([bytes], { type: mime }));
      this.urls.push(url);
      return url;
    }));
  }
  private async fetchAsset(name: string, signal: AbortSignal): Promise<ArrayBuffer> {
    const response = await fetch(WELCOME_ASSET_ROOT + name, { signal });
    if (!response.ok) throw new Error("Tape media could not load");
    return response.arrayBuffer();
  }
  async setClosing(content: ArrayBuffer, signal: AbortSignal): Promise<boolean> {
    const buffer = await this.context.decodeAudioData(content);
    if (signal.aborted || this.isPlaying || this.isDisposed) return false;
    this.buffers[1] = buffer;
    return true;
  }
  get time(): number { return this.elapsed + (this.isPlaying ? this.context.currentTime - this.startedAt : 0); }
  get duration(): number { return 1 + WELCOME_BODY_SECONDS + (this.buffers[1]?.duration ?? 0) + WELCOME_HOLD_SECONDS + WELCOME_BLACK_SECONDS; }
  get mouthIsOpen(): boolean {
    const samples = new Float32Array(this.analyser.fftSize);
    this.analyser.getFloatTimeDomainData(samples);
    const energy = samples.reduce((sum, sample) => sum + sample * sample, 0) / samples.length;
    return energy > 0.0004 && this.time % 0.5 < 0.3;
  }
  setMuted(isMuted: boolean, volume: number): void { this.gain.gain.value = isMuted ? 0 : volume; }
  async play(): Promise<void> {
    if (this.isDisposed || this.buffers.length !== 3) return;
    await this.context.resume();
    if (this.context.state !== "running") throw new Error("Playback needs a gesture");
    if (this.isPlaying || this.isDisposed) return;
    this.startedAt = this.context.currentTime;
    this.isPlaying = true;
    this.schedule(this.buffers[2], 0, true);
    this.schedule(this.buffers[0], 1, false);
    this.schedule(this.buffers[1], 1 + WELCOME_BODY_SECONDS, false);
  }
  private schedule(buffer: AudioBuffer, start: number, isLoop: boolean): void {
    const offset = Math.max(0, this.elapsed - start);
    if (!isLoop && offset >= buffer.duration) return;
    const source = this.context.createBufferSource();
    source.buffer = buffer; source.loop = isLoop;
    source.connect(isLoop ? this.gain : this.analyser);
    source.start(this.context.currentTime + Math.max(0, start - this.elapsed), offset % buffer.duration);
    this.sources.push(source);
  }
  pause(): void {
    this.elapsed = this.time; this.isPlaying = false;
    this.sources.forEach(source => source.stop()); this.sources = [];
  }
  dispose(): void {
    this.isDisposed = true; this.pause(); this.urls.forEach(url => URL.revokeObjectURL(url));
    void this.context.close();
  }
}
