/**
 * Single-clip-at-a-time playback controller for generated narration audio.
 * Unlike ambient-soundtrack.ts's app-wide music engine, playback here is
 * always triggered by a direct user gesture (the per-turn play button) --
 * no autoplay, so no autoplay-policy unlock handling is needed.
 */

type PlaybackListener = (playingTurnId: string | null) => void;
type SpeakerListener = (speaker: string | null) => void;
interface SpeakerSegment { speaker: string; start: number; end: number }

export class NarrationPlaybackController {
  private audio: HTMLAudioElement | null = null;
  private playingTurnId: string | null = null;
  private listeners = new Set<PlaybackListener>();
  private speakerListeners = new Set<SpeakerListener>();
  private speaker: string | null = null;
  private segments: SpeakerSegment[] = [];
  private metadataRequest: AbortController | null = null;

  play(turnId: string, url: string, loadSpeakers = false): void {
    this.stop();
    const audio = new Audio(url);
    audio.onended = () => this.stop();
    audio.onerror = () => this.stop();
    audio.ontimeupdate = () => this.updateSpeaker(audio.currentTime);
    void audio.play();
    this.audio = audio;
    this.playingTurnId = turnId;
    this.notify();
    if (loadSpeakers) void this.loadSpeakerSegments(url, audio);
  }

  stop(): void {
    if (!this.audio && !this.playingTurnId) return;
    if (this.audio) {
      this.audio.pause();
      this.audio.onended = null;
      this.audio.onerror = null;
      this.audio.ontimeupdate = null;
    }
    this.metadataRequest?.abort();
    this.metadataRequest = null;
    this.segments = [];
    this.setSpeaker(null);
    this.audio = null;
    this.playingTurnId = null;
    this.notify();
  }

  getPlayingTurnId(): string | null {
    return this.playingTurnId;
  }

  onPlaybackChange(listener: PlaybackListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onSpeakerChange(listener: SpeakerListener): () => void {
    this.speakerListeners.add(listener);
    return () => this.speakerListeners.delete(listener);
  }

  private async loadSpeakerSegments(url: string, audio: HTMLAudioElement): Promise<void> {
    const request = new AbortController();
    this.metadataRequest = request;
    try {
      const response = await fetch(`${url}.speakers.json`, { signal: request.signal });
      if (!response.ok) return;
      const data: unknown = await response.json();
      if (this.audio !== audio || !data || typeof data !== "object" || !("segments" in data) || !Array.isArray(data.segments)) return;
      this.segments = data.segments.filter((item: unknown): item is SpeakerSegment => {
        if (!item || typeof item !== "object") return false;
        const segment = item as Record<string, unknown>;
        return typeof segment.speaker === "string" && segment.speaker.length > 0 && typeof segment.start === "number" && Number.isFinite(segment.start) && typeof segment.end === "number" && Number.isFinite(segment.end) && segment.start >= 0 && segment.end > segment.start;
      });
      this.updateSpeaker(audio.currentTime);
    } catch { /* Audio remains playable when metadata is unavailable. */ }
  }

  private updateSpeaker(time: number): void {
    this.setSpeaker(this.segments.find((segment) => segment.start <= time && time < segment.end)?.speaker ?? null);
  }

  private setSpeaker(speaker: string | null): void {
    if (speaker === this.speaker) return;
    this.speaker = speaker;
    this.speakerListeners.forEach((listener) => listener(speaker));
  }

  private notify(): void {
    this.listeners.forEach((listener) => listener(this.playingTurnId));
  }
}

export const narrationPlayback = new NarrationPlaybackController();
