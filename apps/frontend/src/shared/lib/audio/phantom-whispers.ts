import {
  bandPass,
  blankSamples,
  onePoleCoefficient,
  scaleToPeak,
  seededRandom,
  TWO_PI,
} from "./synth-primitives";

export const PHANTOM_MAX_GAIN = 0.05;
export const WHISPER_MIN_DELAY_MS = 20000;
export const WHISPER_DELAY_SPAN_MS = 40000;
const WHISPER_MIN_SECONDS = 1.0;
const WHISPER_SECONDS_SPAN = 0.8;
const WHISPER_FORMANT_LOW_HZ = [500, 700, 900];
const WHISPER_FORMANT_HIGH_HZ = [1500, 1900, 2300];
const WHISPER_SYLLABLE_HZ = 3.5;
const WHISPER_PAN = 0.8;

export interface PhantomOutput {
  getContext: () => BaseAudioContext | null;
  playWhisper: (buffer: AudioBuffer, pan: number) => void;
}

export const nextWhisperDelayMs = (random: () => number): number =>
  WHISPER_MIN_DELAY_MS + random() * WHISPER_DELAY_SPAN_MS;

const pickFrom = (choices: number[], random: () => number): number =>
  choices[Math.floor(random() * choices.length)];

// Breathy, vowel-like noise: two formant bands under a slow swell split into
// syllables. Which vowel and how long come from the random stream, so the same
// seed always whispers the same way.
export function synthesizeWhisper(
  context: BaseAudioContext,
  random: () => number,
): AudioBuffer {
  const sampleRate = context.sampleRate;
  const seconds = WHISPER_MIN_SECONDS + random() * WHISPER_SECONDS_SPAN;
  const raw = blankSamples(seconds, sampleRate);
  for (let i = 0; i < raw.length; i += 1) raw[i] = random() * 2 - 1;
  const low = pickFrom(WHISPER_FORMANT_LOW_HZ, random);
  const high = pickFrom(WHISPER_FORMANT_HIGH_HZ, random);
  const samples = bandPass(
    raw,
    onePoleCoefficient(low * 0.6, sampleRate),
    onePoleCoefficient(low * 1.6, sampleRate),
  );
  const upper = bandPass(
    raw,
    onePoleCoefficient(high * 0.7, sampleRate),
    onePoleCoefficient(high * 1.5, sampleRate),
  );
  for (let i = 0; i < samples.length; i += 1) {
    const progress = i / samples.length;
    const swell = Math.sin(Math.PI * progress) ** 2;
    const syllables = 0.55 + 0.45 * Math.sin(TWO_PI * WHISPER_SYLLABLE_HZ * (i / sampleRate));
    samples[i] = (samples[i] + 0.6 * upper[i]) * swell * syllables;
  }
  scaleToPeak(samples, 1);
  const buffer = context.createBuffer(1, samples.length, sampleRate);
  buffer.getChannelData(0).set(samples);
  return buffer;
}

// Schedules faint whispers from the left or right at uneven intervals. The
// schedule is seeded (by the playthrough id), so a reload replays the same
// pattern of gaps. Sounds the browser has not allowed yet are dropped.
export class PhantomWhispers {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private seed: string | null = null;
  private random: () => number = Math.random;

  constructor(private readonly output: PhantomOutput) {}

  public start(seed: string): void {
    if (this.seed === seed) return;
    this.stop();
    this.seed = seed;
    this.random = seededRandom(seed);
    this.scheduleNext();
  }

  public stop(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.seed = null;
  }

  private scheduleNext(): void {
    this.timer = setTimeout(() => {
      this.whisper();
      if (this.seed !== null) this.scheduleNext();
    }, nextWhisperDelayMs(this.random));
  }

  private whisper(): void {
    const context = this.output.getContext();
    if (!context || (context as AudioContext).state !== "running") return;
    const pan = this.random() < 0.5 ? -WHISPER_PAN : WHISPER_PAN;
    this.output.playWhisper(synthesizeWhisper(context, this.random), pan);
  }
}
