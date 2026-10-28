import { ScenarioMood } from "@/shared/types/audio.types";
import { SensoryCueId } from "@/shared/constants/sensory-cues";
import {
  PHANTOM_MAX_GAIN,
  PhantomOutput,
  PhantomWhispers,
} from "./phantom-whispers";
import { SfxFileLoader, SfxPlayer, fetchSfxFile } from "./sfx-player";
import {
  recordAudioBlocked,
  recordPlayRejected,
  recordSfxPlayed,
} from "../alpha-audio-telemetry";
import { synthesizeCue } from "./sfx-synth";

const CROSSFADE_DURATION_SECONDS = 4.0;
const MIN_COOLDOWN_MS = 45000;
const GAIN_MIN = 0.0001;
const STORAGE_KEY_VOLUME = "sands_audio_volume";
const STORAGE_KEY_MUTED = "sands_audio_muted";
const MS_PER_SECOND = 1000;
const HARD_MUTE_DEFAULT_MS = 30;

interface AudioChannel {
  element: HTMLAudioElement;
  sourceNode: MediaElementAudioSourceNode | null;
  gainNode: GainNode | null;
  fadeTimeoutId?: ReturnType<typeof setTimeout> | null;
  trackUrl?: string;
  onLoadError?: () => void;
}

export interface TransitionOptions {
  isForce?: boolean;
  crossfadeSeconds?: number;
  /** Played instead when `trackUrl` fails to load. */
  fallbackUrl?: string;
}

export interface AmbientSoundtrackOptions {
  sfxFileLoader?: SfxFileLoader;
}

export type MoodListener = (mood: ScenarioMood) => void;
export type AudioPreferenceListener = (preferences: {
  volume: number;
  isMuted: boolean;
}) => void;

export class AmbientSoundtrackController {
  private audioContext: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private channelA: AudioChannel | null = null;
  private channelB: AudioChannel | null = null;
  private activeChannelIndex: 0 | 1 = 0;
  private currentMood: ScenarioMood | null = null;
  private currentTrackUrl: string | null = null;
  private pendingChannel: AudioChannel | null = null;
  private lastTransitionTime = 0;
  private volume = 0.6;
  private isMuted = false;
  private isUnlocked = false;
  private moodListeners: Set<MoodListener> = new Set();
  private audioPreferenceListeners: Set<AudioPreferenceListener> = new Set();
  private sfxPlayer: SfxPlayer | null = null;
  private phantomWhispers: PhantomWhispers | null = null;
  private isAmbientCut = false;
  private readonly activeSfxGains: Set<GainNode> = new Set();
  private readonly sfxFileLoader: SfxFileLoader;

  constructor(options: AmbientSoundtrackOptions = {}) {
    this.sfxFileLoader = options.sfxFileLoader ?? fetchSfxFile;
    this.loadSavedPreferences();
  }

  public onMoodChange(listener: MoodListener): () => void {
    this.moodListeners.add(listener);
    return () => {
      this.moodListeners.delete(listener);
    };
  }

  private notifyMoodChange(mood: ScenarioMood): void {
    for (const listener of this.moodListeners) {
      try {
        listener(mood);
      } catch {
        // Suppress listener error
      }
    }
  }

  public getMood(): ScenarioMood | null {
    return this.currentMood;
  }

  public getCurrentTrackUrl(): string | null {
    return this.currentTrackUrl;
  }

  public getVolume(): number {
    return this.volume;
  }

  public getIsMuted(): boolean {
    return this.isMuted;
  }

  /** Lets isolated audio features honor the player-wide audio preference
   * without importing the play store. */
  public onAudioPreferenceChange(
    listener: AudioPreferenceListener,
  ): () => void {
    this.audioPreferenceListeners.add(listener);
    return () => this.audioPreferenceListeners.delete(listener);
  }

  private notifyAudioPreferenceChange(): void {
    const preferences = { volume: this.volume, isMuted: this.isMuted };
    for (const listener of this.audioPreferenceListeners) {
      try {
        listener(preferences);
      } catch {
        // An optional audio consumer must not break global audio controls.
      }
    }
  }

  public init(): void {
    if (typeof window === "undefined" || this.audioContext) return;
    this.setupAudioContext();
    this.setupAutoplayUnlock();
  }

  public setVolume(vol: number): void {
    this.volume = Math.max(0.0, Math.min(1.0, vol));
    this.savePreferences();
    this.applyPreferencesToOutputs();
    this.notifyAudioPreferenceChange();
  }

  public toggleMute(): boolean {
    this.isMuted = !this.isMuted;
    this.savePreferences();
    this.applyPreferencesToOutputs();
    this.notifyAudioPreferenceChange();
    return this.isMuted;
  }

  /** A volume or mute change lands at once, even in the middle of a resume ramp
   * or a playing cue: scheduled ramps are cancelled so they cannot undo it. The
   * ambience stays at zero while it is cut, and comes back at the new volume on
   * resume. */
  private applyPreferencesToOutputs(): void {
    if (!this.audioContext) return;
    const now = this.audioContext.currentTime;
    if (this.masterGain) {
      const target = this.isAmbientCut || this.isMuted ? 0 : this.volume;
      this.masterGain.gain.cancelScheduledValues(now);
      this.masterGain.gain.setValueAtTime(target, now);
    }
    const sfxTarget = this.isMuted ? 0 : this.volume;
    for (const gain of this.activeSfxGains) {
      gain.gain.setValueAtTime(sfxTarget, now);
    }
  }

  public transitionTo(
    newMood: ScenarioMood,
    trackUrl: string | undefined = undefined,
    options: boolean | TransitionOptions = false,
  ): boolean {
    const {
      isForce = false,
      crossfadeSeconds = CROSSFADE_DURATION_SECONDS,
      fallbackUrl,
    } = typeof options === "boolean" ? { isForce: options } : options;
    if (!trackUrl) return false;
    if (!this.shouldAllowTransition(newMood, trackUrl, isForce)) {
      return false;
    }

    this.init();
    this.ensureContextRunning();
    this.executeCrossfade(trackUrl, crossfadeSeconds, fallbackUrl);
    this.currentMood = newMood;
    this.currentTrackUrl = trackUrl;
    this.lastTransitionTime = Date.now();
    this.notifyMoodChange(newMood);
    return true;
  }

  /** Cuts the ambience to silence almost instantly (default 30 ms). The cue
   * sounds play outside the master gain, so this never silences them. */
  public hardMute(durationMs: number = HARD_MUTE_DEFAULT_MS): void {
    this.init();
    if (!this.masterGain || !this.audioContext) return;
    this.isAmbientCut = true;
    const now = this.audioContext.currentTime;
    const gain = this.masterGain.gain;
    gain.cancelScheduledValues(now);
    gain.setValueAtTime(gain.value, now);
    gain.linearRampToValueAtTime(0, now + durationMs / MS_PER_SECOND);
  }

  /** Brings the ambience back to the player's own volume; a player who muted
   * the game stays muted. */
  public resumeAmbient(rampMs: number): void {
    if (!this.masterGain || !this.audioContext) return;
    this.isAmbientCut = false;
    const now = this.audioContext.currentTime;
    const target = this.isMuted ? 0 : this.volume;
    this.masterGain.gain.cancelScheduledValues(now);
    this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, now);
    this.masterGain.gain.linearRampToValueAtTime(
      target,
      now + rampMs / MS_PER_SECOND,
    );
  }

  /** Waits `leadSilenceMs`, then plays the cue and resolves when it ends. A
   * recorded file is preferred and the synthesised sound is the fallback; the
   * sound is fetched during the dead air so it never delays the cue. It follows
   * the player's volume and mute, and is dropped (never replayed late) when the
   * browser has not allowed audio yet. */
  public async playSfx(
    cueId: SensoryCueId,
    options: { leadSilenceMs: number },
  ): Promise<void> {
    this.init();
    const loading = this.getSfxPlayer()?.getBuffer(cueId);
    await new Promise<void>((resolve) =>
      setTimeout(resolve, options.leadSilenceMs),
    );
    this.ensureContextRunning();
    const context = this.audioContext;
    if (!context || context.state !== "running") {
      recordAudioBlocked("autoplay_policy");
      return;
    }
    if (this.isMuted) {
      recordAudioBlocked("muted");
    } else {
      recordSfxPlayed();
    }
    await this.playBuffer(context, (await loading) ?? synthesizeCue(context, cueId));
  }

  private getSfxPlayer(): SfxPlayer | null {
    if (!this.audioContext) return null;
    this.sfxPlayer ??= new SfxPlayer(this.audioContext, this.sfxFileLoader);
    return this.sfxPlayer;
  }

  private playBuffer(context: AudioContext, buffer: AudioBuffer): Promise<void> {
    const gain = context.createGain();
    gain.gain.value = this.isMuted ? 0 : this.volume;
    gain.connect(context.destination);
    this.activeSfxGains.add(gain);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(gain);
    return new Promise<void>((resolve) => {
      source.onended = () => {
        this.activeSfxGains.delete(gain);
        resolve();
      };
      source.start();
    });
  }

  /** Level 1 starts the faint phantom whispers (scheduled from `seed`, so a
   * reload keeps the same rhythm); level 0 stops them. They play through the
   * master gain, so a hard cut, mute and volume all apply to them. */
  public setPhantomAmbience(level: 0 | 1, seed: string = ""): void {
    if (level === 0) {
      this.phantomWhispers?.stop();
      return;
    }
    this.init();
    this.phantomWhispers ??= new PhantomWhispers(this.createPhantomOutput());
    this.phantomWhispers.start(seed);
  }

  private createPhantomOutput(): PhantomOutput {
    return {
      getContext: () => this.audioContext,
      playWhisper: (buffer, pan) => this.playPhantomBuffer(buffer, pan),
    };
  }

  private playPhantomBuffer(buffer: AudioBuffer, pan: number): void {
    const context = this.audioContext;
    if (!context || !this.masterGain) return;
    const gain = context.createGain();
    gain.gain.value = PHANTOM_MAX_GAIN;
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(gain);
    if (typeof context.createStereoPanner === "function") {
      const panner = context.createStereoPanner();
      panner.pan.value = pan;
      gain.connect(panner);
      panner.connect(this.masterGain);
    } else {
      gain.connect(this.masterGain);
    }
    source.start();
  }

  public stop(): void {
    this.phantomWhispers?.stop();
    if (this.channelA) {
      if (this.channelA.fadeTimeoutId) {
        clearTimeout(this.channelA.fadeTimeoutId);
        this.channelA.fadeTimeoutId = null;
      }
      this.channelA.element.pause();
    }
    if (this.channelB) {
      if (this.channelB.fadeTimeoutId) {
        clearTimeout(this.channelB.fadeTimeoutId);
        this.channelB.fadeTimeoutId = null;
      }
      this.channelB.element.pause();
    }
    this.currentMood = null;
    this.currentTrackUrl = null;
    this.pendingChannel = null;
  }

  private shouldAllowTransition(
    newMood: ScenarioMood,
    trackUrl: string,
    isForce: boolean,
  ): boolean {
    if (newMood === this.currentMood && trackUrl === this.currentTrackUrl) {
      return false;
    }
    if (isForce || newMood === "combat") return true;

    const timeSinceLast = Date.now() - this.lastTransitionTime;
    return timeSinceLast >= MIN_COOLDOWN_MS;
  }

  private setupAudioContext(): void {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;
    if (!AudioCtx) return;

    this.audioContext = new AudioCtx();
    this.masterGain = this.audioContext.createGain();
    this.masterGain.gain.value = this.isMuted ? 0 : this.volume;
    this.masterGain.connect(this.audioContext.destination);

    this.channelA = this.createChannel();
    this.channelB = this.createChannel();
  }

  private createChannel(): AudioChannel {
    const audio = new Audio();
    audio.loop = true;
    audio.preload = "auto";
    // Mood tracks are served cross-origin from GCS. createMediaElementSource
    // below routes this element's output through the Web Audio graph, and
    // without crossOrigin set the element is CORS-opaque -- Web Audio mutes
    // it entirely ("MediaElementAudioSource outputs zeroes") even though the
    // element itself would play fine on its own. Requires the GCS bucket to
    // answer with Access-Control-Allow-Origin for this to actually work.
    audio.crossOrigin = "anonymous";
    let sourceNode: MediaElementAudioSourceNode | null = null;
    let gainNode: GainNode | null = null;

    if (this.audioContext && this.masterGain) {
      try {
        sourceNode = this.audioContext.createMediaElementSource(audio);
        gainNode = this.audioContext.createGain();
        gainNode.gain.value = GAIN_MIN;
        sourceNode.connect(gainNode);
        gainNode.connect(this.masterGain);
      } catch {
        // Fallback for restricted test/headless contexts
      }
    }

    return { element: audio, sourceNode, gainNode };
  }

  private executeCrossfade(
    trackUrl: string,
    crossfadeSeconds: number,
    fallbackUrl: string | undefined,
  ): void {
    if (!this.channelA || !this.channelB || !this.audioContext) return;

    const outgoing =
      this.activeChannelIndex === 0 ? this.channelA : this.channelB;
    const incoming =
      this.activeChannelIndex === 0 ? this.channelB : this.channelA;
    this.activeChannelIndex = this.activeChannelIndex === 0 ? 1 : 0;

    const now = this.audioContext.currentTime;
    this.fadeChannelOut(outgoing, now, crossfadeSeconds);
    this.fadeChannelIn(incoming, trackUrl, now, crossfadeSeconds);
    this.armLoadFallback(incoming, trackUrl, fallbackUrl);
  }

  private armLoadFallback(
    channel: AudioChannel,
    trackUrl: string,
    fallbackUrl: string | undefined,
  ): void {
    if (channel.onLoadError) {
      channel.element.removeEventListener("error", channel.onLoadError);
      channel.onLoadError = undefined;
    }
    if (!fallbackUrl || fallbackUrl === trackUrl) return;
    const handleLoadError = (): void => {
      if (channel.trackUrl !== trackUrl || this.currentTrackUrl !== trackUrl) {
        return;
      }
      channel.trackUrl = fallbackUrl;
      this.currentTrackUrl = fallbackUrl;
      channel.element.src = fallbackUrl;
      channel.element.play().catch(recordPlayRejected);
    };
    channel.onLoadError = handleLoadError;
    channel.element.addEventListener("error", handleLoadError, { once: true });
  }

  private fadeChannelOut(
    channel: AudioChannel,
    now: number,
    crossfadeSeconds: number,
  ): void {
    if (channel.fadeTimeoutId) {
      clearTimeout(channel.fadeTimeoutId);
      channel.fadeTimeoutId = null;
    }

    if (!channel.gainNode || !this.audioContext) {
      channel.element.pause();
      return;
    }

    const currentGain = Math.max(channel.gainNode.gain.value, GAIN_MIN);
    channel.gainNode.gain.cancelScheduledValues(now);
    channel.gainNode.gain.setValueAtTime(currentGain, now);
    channel.gainNode.gain.exponentialRampToValueAtTime(
      GAIN_MIN,
      now + crossfadeSeconds,
    );

    channel.fadeTimeoutId = setTimeout(() => {
      channel.element.pause();
      channel.fadeTimeoutId = null;
    }, crossfadeSeconds * MS_PER_SECOND);
  }

  private fadeChannelIn(
    channel: AudioChannel,
    trackUrl: string,
    now: number,
    crossfadeSeconds: number,
  ): void {
    if (channel.fadeTimeoutId) {
      clearTimeout(channel.fadeTimeoutId);
      channel.fadeTimeoutId = null;
    }

    channel.trackUrl = trackUrl;
    channel.element.src = trackUrl;
    const playPromise = channel.element.play();
    if (playPromise !== undefined) {
      playPromise
        .then(() => {
          if (this.pendingChannel === channel) this.pendingChannel = null;
        })
        .catch((error: unknown) => {
          this.pendingChannel = channel;
          recordPlayRejected(error);
        });
    }

    if (!channel.gainNode || !this.audioContext) return;
    // NOTE: a still-pending ramp from an earlier transition would otherwise
    // run after this one and drag the incoming channel back to silence.
    channel.gainNode.gain.cancelScheduledValues(now);
    channel.gainNode.gain.setValueAtTime(GAIN_MIN, now);
    channel.gainNode.gain.exponentialRampToValueAtTime(
      1.0,
      now + crossfadeSeconds,
    );
  }

  private ensureContextRunning(): void {
    if (this.audioContext?.state === "suspended") {
      void this.audioContext.resume();
    }
  }

  private resumePendingChannel(): void {
    const channel = this.pendingChannel;
    if (!channel) return;
    this.pendingChannel = null;
    channel.element.play().catch(() => {
      // Still blocked; nothing more to do until the next user gesture.
    });
  }

  private setupAutoplayUnlock(): void {
    if (this.isUnlocked || typeof window === "undefined") return;

    const unlockHandler = () => {
      this.isUnlocked = true;
      this.ensureContextRunning();
      this.resumePendingChannel();
      window.removeEventListener("pointerdown", unlockHandler);
      window.removeEventListener("keydown", unlockHandler);
    };

    window.addEventListener("pointerdown", unlockHandler, { once: true });
    window.addEventListener("keydown", unlockHandler, { once: true });
  }

  private loadSavedPreferences(): void {
    if (typeof localStorage === "undefined") return;
    const savedVol = localStorage.getItem(STORAGE_KEY_VOLUME);
    if (savedVol !== null) {
      const parsed = parseFloat(savedVol);
      if (!isNaN(parsed)) this.volume = Math.max(0.0, Math.min(1.0, parsed));
    }
    const savedMute = localStorage.getItem(STORAGE_KEY_MUTED);
    if (savedMute !== null) {
      this.isMuted = savedMute === "true";
    }
  }

  private savePreferences(): void {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(STORAGE_KEY_VOLUME, this.volume.toString());
    localStorage.setItem(STORAGE_KEY_MUTED, this.isMuted.toString());
  }
}

export const ambientSoundtrack = new AmbientSoundtrackController();
