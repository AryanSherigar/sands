import type { ComposureAudioProfile } from "@/shared/types/minigame.types";

// All sound is synthesised in Web Audio; no asset files are loaded.
const MASTER_LEVEL = 0.8;
const THUD_HZ = 46;
const THUD_SECONDS = 0.32;
const THUD_LEVEL = 0.9;
const HUM_HZ = 196;
const HUM_SECONDS = 0.45;
const HUM_LEVEL = 0.12;
const STEP_SECONDS = 0.06;
const STEP_BASE_LEVEL = 0.04;
const STEP_LEVEL_PER_STRIKE = 0.05;
const STEP_PAN = -0.8;
const HUM_PROFILE_STEP_LEVEL = 0.02;
const GASP_SECONDS = 0.2;
const GASP_LEVEL = 0.2;
const NOISE_SEED = 7;
const LCG_MULTIPLIER = 1664525;
const LCG_INCREMENT = 1013904223;
const LCG_MODULUS = 2 ** 32;
const MIN_GAIN = 0.0001;
const WIN_NOTES_HZ = [196, 247, 294];
const LOSE_NOTES_HZ = [147, 123, 98];
const NOTE_SPACING_SECONDS = 0.18;
const NOTE_SECONDS = 0.5;
const NOTE_LEVEL = 0.18;

export interface ComposureAudioPort {
  scheduleBeat: (atSeconds: number, strikes: number) => void;
  playHit: () => void;
  playStrike: () => void;
  playOutcome: (outcome: "win" | "lose") => void;
}

export class ComposureAudio implements ComposureAudioPort {
  private readonly master: GainNode;
  private readonly noise: AudioBuffer;

  constructor(
    private readonly context: AudioContext,
    private readonly profile: ComposureAudioProfile,
  ) {
    this.master = context.createGain();
    this.master.gain.value = MASTER_LEVEL;
    this.master.connect(context.destination);
    this.noise = this.buildNoise();
  }

  public scheduleBeat(atSeconds: number, strikes: number): void {
    this.tone("sine", THUD_HZ, atSeconds, THUD_SECONDS, THUD_LEVEL);
    const stepLevel =
      this.profile === "chase"
        ? STEP_BASE_LEVEL + STEP_LEVEL_PER_STRIKE * strikes
        : HUM_PROFILE_STEP_LEVEL;
    this.step(atSeconds + STEP_SECONDS, stepLevel);
    if (this.profile === "chase" && strikes > 0) {
      this.step(atSeconds + STEP_SECONDS * 3, stepLevel);
    }
  }

  public playHit(): void {
    this.tone("triangle", HUM_HZ, this.context.currentTime, HUM_SECONDS, HUM_LEVEL);
  }

  public playStrike(): void {
    this.noiseBurst(this.context.currentTime, GASP_SECONDS, GASP_LEVEL, 0);
  }

  public playOutcome(outcome: "win" | "lose"): void {
    const notes = outcome === "win" ? WIN_NOTES_HZ : LOSE_NOTES_HZ;
    notes.forEach((hz, index) => {
      const at = this.context.currentTime + index * NOTE_SPACING_SECONDS;
      this.tone("sine", hz, at, NOTE_SECONDS, NOTE_LEVEL);
    });
  }

  public close(): void {
    void this.context.close();
  }

  private tone(
    type: OscillatorType,
    hz: number,
    atSeconds: number,
    seconds: number,
    level: number,
  ): void {
    const oscillator = this.context.createOscillator();
    const gain = this.context.createGain();
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(hz, atSeconds);
    gain.gain.setValueAtTime(level, atSeconds);
    gain.gain.exponentialRampToValueAtTime(MIN_GAIN, atSeconds + seconds);
    oscillator.connect(gain);
    gain.connect(this.master);
    oscillator.start(atSeconds);
    oscillator.stop(atSeconds + seconds);
  }

  private step(atSeconds: number, level: number): void {
    this.noiseBurst(atSeconds, STEP_SECONDS, level, STEP_PAN);
  }

  private noiseBurst(
    atSeconds: number,
    seconds: number,
    level: number,
    pan: number,
  ): void {
    const source = this.context.createBufferSource();
    const gain = this.context.createGain();
    const panner = this.context.createStereoPanner();
    source.buffer = this.noise;
    panner.pan.value = pan;
    gain.gain.setValueAtTime(level, atSeconds);
    gain.gain.exponentialRampToValueAtTime(MIN_GAIN, atSeconds + seconds);
    source.connect(gain);
    gain.connect(panner);
    panner.connect(this.master);
    source.start(atSeconds);
    source.stop(atSeconds + seconds);
  }

  private buildNoise(): AudioBuffer {
    const length = Math.floor(this.context.sampleRate * GASP_SECONDS);
    const buffer = this.context.createBuffer(1, length, this.context.sampleRate);
    const samples = buffer.getChannelData(0);
    let state = NOISE_SEED;
    for (let i = 0; i < length; i += 1) {
      state = (LCG_MULTIPLIER * state + LCG_INCREMENT) % LCG_MODULUS;
      samples[i] = (state / LCG_MODULUS) * 2 - 1;
    }
    return buffer;
  }
}
