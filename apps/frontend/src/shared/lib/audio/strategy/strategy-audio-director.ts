import type {
  StrategyAudioDirectorOptions,
  StrategyAudioTarget,
  StrategyStingerEvent,
} from "@/shared/types/strategy-audio.types";
import { MoodDeck } from "./mood-deck";

export const GAIN_EPSILON = 0.0001;
export const CROSSFADE_SECONDS = 3.0;

export const FALLBACK_MOOD_MAP: Record<string, string> = {
  pax: "/audio/moods/peaceful.wav",
  vigilance: "/audio/moods/tension.wav",
  war: "/audio/moods/combat.wav",
  desolation: "/audio/moods/melancholy.wav",
  court: "/audio/moods/mystery.wav",
  study: "/audio/moods/peaceful.wav",
  tactical: "/audio/moods/tension.wav",
  arid: "/audio/moods/mystery.wav",
  plains: "/audio/moods/peaceful.wav",
  coast: "/audio/moods/peaceful.wav",
  mountains: "/audio/moods/mystery.wav",
};

// NOTE: only stems that exist under public/audio/strategy are listed; every other key
// resolves through FALLBACK_MOOD_MAP so playback never requests a missing file.
export const STRATEGY_TRACK_MAP: Record<string, string> = {
  pax: "/audio/strategy/stems/pax.mp3",
  vigilance: "/audio/strategy/stems/vigilance.mp3",
  war: "/audio/strategy/stems/war.mp3",
  desolation: "/audio/strategy/stems/desolation.mp3",
};

export function resolveStrategyTrackUrl(trackKey: string): string {
  return STRATEGY_TRACK_MAP[trackKey] ?? FALLBACK_MOOD_MAP[trackKey] ?? "/audio/moods/peaceful.wav";
}

export class StrategyAudioDirector {
  private audioContext: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private ambientGain: GainNode | null = null;
  private moodGain: GainNode | null = null;
  private contextGain: GainNode | null = null;
  private stingerGain: GainNode | null = null;
  private winterFilter: BiquadFilterNode | null = null;

  private volume: number;
  private isMuted: boolean;
  private isUnlocked = false;
  private currentTarget: StrategyAudioTarget | null = null;
  private moodDeck: MoodDeck | null = null;
  private currentMoodTrackKey: string | null = null;

  constructor(options: StrategyAudioDirectorOptions = {}) {
    this.volume = options.volume ?? 0.7;
    this.isMuted = options.isMuted ?? false;
  }

  private ensureContext(): void {
    if (this.audioContext) return;
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioCtx) return;

    this.audioContext = new AudioCtx();
    const now = this.audioContext.currentTime;

    this.masterGain = this.audioContext.createGain();
    const initialMaster = this.isMuted
      ? GAIN_EPSILON
      : Math.max(GAIN_EPSILON, this.volume);
    this.masterGain.gain.setValueAtTime(initialMaster, now);

    this.ambientGain = this.audioContext.createGain();
    this.moodGain = this.audioContext.createGain();
    this.contextGain = this.audioContext.createGain();
    this.stingerGain = this.audioContext.createGain();

    this.winterFilter = this.audioContext.createBiquadFilter();
    this.winterFilter.type = "lowpass";
    this.winterFilter.frequency.setValueAtTime(20000, now);

    this.ambientGain.connect(this.winterFilter);
    this.winterFilter.connect(this.masterGain);
    this.moodGain.connect(this.masterGain);
    this.contextGain.connect(this.masterGain);
    this.stingerGain.connect(this.masterGain);

    this.masterGain.connect(this.audioContext.destination);
  }

  public unlock(): void {
    if (this.isUnlocked || !this.audioContext) return;
    if (this.audioContext.state === "suspended") {
      void this.audioContext
        .resume()
        .then(() => {
          this.isUnlocked = true;
          this.playMoodAudio();
        })
        .catch(() => {});
    } else {
      this.isUnlocked = true;
      this.playMoodAudio();
    }
  }

  private playMoodAudio(): void {
    this.moodDeck?.play();
  }

  private ensureMoodDeck(): MoodDeck | null {
    if (this.moodDeck) return this.moodDeck;
    if (typeof Audio === "undefined") return null;
    this.moodDeck = new MoodDeck({
      fadeSeconds: CROSSFADE_SECONDS,
      attachChannel: (element) => this.attachToMoodBus(element),
      resolveFallbackUrl: () =>
        this.currentMoodTrackKey ? (FALLBACK_MOOD_MAP[this.currentMoodTrackKey] ?? null) : null,
    });
    return this.moodDeck;
  }

  private attachToMoodBus(element: HTMLAudioElement): void {
    if (
      !this.audioContext ||
      !this.moodGain ||
      typeof this.audioContext.createMediaElementSource !== "function"
    ) {
      return;
    }
    try {
      this.audioContext.createMediaElementSource(element).connect(this.moodGain);
    } catch {
      // NOTE: an element can only be wrapped once; a repeat attach is harmless.
    }
  }

  public applyTarget(target: StrategyAudioTarget): void {
    this.currentTarget = target;
    this.ensureContext();
    if (!this.audioContext) return;

    const now = this.audioContext.currentTime;

    // 1. Ambient & Winter filter
    if (this.ambientGain) {
      const targetGain = Math.max(GAIN_EPSILON, target.ambientGain);
      this.ambientGain.gain.setValueAtTime(this.ambientGain.gain.value, now);
      this.ambientGain.gain.exponentialRampToValueAtTime(
        targetGain,
        now + CROSSFADE_SECONDS,
      );
    }
    if (this.winterFilter) {
      const cutoff = target.isWinterMuffled ? 400 : 20000;
      this.winterFilter.frequency.setValueAtTime(
        this.winterFilter.frequency.value,
        now,
      );
      this.winterFilter.frequency.exponentialRampToValueAtTime(
        cutoff,
        now + CROSSFADE_SECONDS,
      );
    }

    // 2. Strategic Mood Gain & Playback
    if (target.strategicMood !== this.currentMoodTrackKey) {
      this.currentMoodTrackKey = target.strategicMood;
      this.ensureMoodDeck()?.crossfadeTo(
        resolveStrategyTrackUrl(target.strategicMood),
        this.isUnlocked,
      );
    }

    if (this.moodGain) {
      const targetGain = Math.max(GAIN_EPSILON, target.moodGain);
      this.moodGain.gain.setValueAtTime(this.moodGain.gain.value, now);
      this.moodGain.gain.exponentialRampToValueAtTime(
        targetGain,
        now + CROSSFADE_SECONDS,
      );
    }

    // 3. UI Context Focus Gain
    if (this.contextGain) {
      const targetGain = Math.max(GAIN_EPSILON, target.contextGain);
      this.contextGain.gain.setValueAtTime(this.contextGain.gain.value, now);
      this.contextGain.gain.exponentialRampToValueAtTime(targetGain, now + 1.0);
    }

    // 4. Stinger one-shot
    if (target.pendingStinger) {
      this.playStinger(target.pendingStinger);
    }
  }

  public playStinger(_stinger: StrategyStingerEvent): void {
    // NOTE: no stinger audio files ship yet, so this only prepares the graph; add stems before scheduling cues.
    this.ensureContext();
  }

  public setVolume(vol: number): void {
    this.volume = Math.max(0, Math.min(1, vol));
    if (this.masterGain && this.audioContext && !this.isMuted) {
      const now = this.audioContext.currentTime;
      this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, now);
      this.masterGain.gain.exponentialRampToValueAtTime(
        Math.max(GAIN_EPSILON, this.volume),
        now + 0.1,
      );
    }
  }

  public getVolume(): number {
    return this.volume;
  }

  public setIsMuted(muted: boolean): void {
    this.isMuted = muted;
    if (this.masterGain && this.audioContext) {
      const now = this.audioContext.currentTime;
      const targetGain = this.isMuted
        ? GAIN_EPSILON
        : Math.max(GAIN_EPSILON, this.volume);
      this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, now);
      this.masterGain.gain.exponentialRampToValueAtTime(targetGain, now + 0.1);
    }
  }

  public getIsMuted(): boolean {
    return this.isMuted;
  }

  public getCurrentTarget(): StrategyAudioTarget | null {
    return this.currentTarget;
  }

  public destroy(): void {
    this.moodDeck?.destroy();
    this.moodDeck = null;
    this.currentMoodTrackKey = null;
    if (this.audioContext && this.audioContext.state !== "closed") {
      void this.audioContext.close().catch(() => {});
    }
    this.audioContext = null;
    this.masterGain = null;
    this.ambientGain = null;
    this.moodGain = null;
    this.contextGain = null;
    this.stingerGain = null;
    this.winterFilter = null;
    this.isUnlocked = false;
    this.currentTarget = null;
  }
}
