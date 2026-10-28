/**
 * Single-clip-at-a-time playback controller for generated narration audio.
 * Unlike ambient-soundtrack.ts's app-wide music engine, playback here is
 * always triggered by a direct user gesture (the per-turn play button) --
 * no autoplay, so no autoplay-policy unlock handling is needed.
 */

type PlaybackListener = (playingTurnId: string | null) => void;

export class NarrationPlaybackController {
  private audio: HTMLAudioElement | null = null;
  private playingTurnId: string | null = null;
  private listeners = new Set<PlaybackListener>();

  play(turnId: string, url: string): void {
    this.stop();
    const audio = new Audio(url);
    audio.onended = () => this.stop();
    audio.onerror = () => this.stop();
    void audio.play();
    this.audio = audio;
    this.playingTurnId = turnId;
    this.notify();
  }

  stop(): void {
    if (!this.audio && !this.playingTurnId) return;
    if (this.audio) {
      this.audio.pause();
      this.audio.onended = null;
      this.audio.onerror = null;
    }
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

  private notify(): void {
    this.listeners.forEach((listener) => listener(this.playingTurnId));
  }
}

export const narrationPlayback = new NarrationPlaybackController();
