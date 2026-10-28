import { seededUnit } from "@/shared/lib/hud/seededUnit";

export const TWO_PI = Math.PI * 2;
const LCG_MULTIPLIER = 1664525;
const LCG_INCREMENT = 1013904223;
const LCG_MODULUS = 2 ** 32;
const EDGE_FADE_SECONDS = 0.006;

// A seeded noise source in [-1, 1) keeps every render identical, so sounds are
// testable.
export const noiseSource = (seed: number): (() => number) => {
  let state = seed;
  return () => {
    state = (LCG_MULTIPLIER * state + LCG_INCREMENT) % LCG_MODULUS;
    return (state / LCG_MODULUS) * 2 - 1;
  };
};

// A seeded random source in [0, 1) for choices (timing, panning) rather than
// sound. Draws are independent of how many were taken before in other seeds.
export const seededRandom = (seed: string): (() => number) => {
  let draw = 0;
  return () => {
    draw += 1;
    return seededUnit(seed, draw);
  };
};

export const blankSamples = (seconds: number, sampleRate: number): Float32Array =>
  new Float32Array(Math.floor(seconds * sampleRate));

export interface ToneSpec {
  startSeconds: number;
  durationSeconds: number;
  hz: number;
  level: number;
  decaySeconds: number;
  attackSeconds?: number;
  endHz?: number;
}

// Adds a sine with an exponential decay. `endHz` glides the pitch (a knock
// thumps downward); the phase is integrated so the glide never clicks.
export function addTone(
  samples: Float32Array,
  sampleRate: number,
  spec: ToneSpec,
): void {
  const offset = Math.floor(spec.startSeconds * sampleRate);
  const length = Math.floor(spec.durationSeconds * sampleRate);
  const attackSamples = Math.max(1, Math.floor((spec.attackSeconds ?? 0.004) * sampleRate));
  let phase = 0;
  for (let i = 0; i < length && offset + i < samples.length; i += 1) {
    const progress = i / length;
    const hz = spec.hz + ((spec.endHz ?? spec.hz) - spec.hz) * progress;
    phase += (TWO_PI * hz) / sampleRate;
    const decay = Math.exp(-(i / sampleRate) / spec.decaySeconds);
    const attack = Math.min(1, i / attackSamples);
    samples[offset + i] += Math.sin(phase) * spec.level * decay * attack;
  }
}

export interface NoiseBurstSpec {
  startSeconds: number;
  durationSeconds: number;
  level: number;
  decaySeconds: number;
  smoothing?: number;
}

// Adds a decaying burst of noise. `smoothing` (0-1) is a one-pole low-pass
// coefficient: small values muffle the burst, 1 leaves it bright.
export function addNoiseBurst(
  samples: Float32Array,
  sampleRate: number,
  nextNoise: () => number,
  spec: NoiseBurstSpec,
): void {
  const offset = Math.floor(spec.startSeconds * sampleRate);
  const length = Math.floor(spec.durationSeconds * sampleRate);
  const smoothing = spec.smoothing ?? 1;
  let filtered = 0;
  for (let i = 0; i < length && offset + i < samples.length; i += 1) {
    filtered += smoothing * (nextNoise() - filtered);
    const decay = Math.exp(-(i / sampleRate) / spec.decaySeconds);
    samples[offset + i] += filtered * spec.level * decay;
  }
}

// Band-passes a signal as the difference of two one-pole low-passes.
export function bandPass(
  input: Float32Array,
  lowCoefficient: number,
  highCoefficient: number,
): Float32Array {
  const output = new Float32Array(input.length);
  let slow = 0;
  let fast = 0;
  for (let i = 0; i < input.length; i += 1) {
    fast += highCoefficient * (input[i] - fast);
    slow += lowCoefficient * (input[i] - slow);
    output[i] = fast - slow;
  }
  return output;
}

// Fades both ends so a sound never starts or stops with a click.
export function fadeEdges(
  samples: Float32Array,
  sampleRate: number,
  seconds: number = EDGE_FADE_SECONDS,
): void {
  const edge = Math.max(1, Math.floor(seconds * sampleRate));
  for (let i = 0; i < edge && i < samples.length; i += 1) {
    const gain = i / edge;
    samples[i] *= gain;
    samples[samples.length - 1 - i] *= gain;
  }
}

const peakOf = (samples: Float32Array): number =>
  samples.reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);

export function scaleToPeak(samples: Float32Array, targetPeak: number): void {
  const peak = peakOf(samples);
  if (peak === 0) return;
  const factor = targetPeak / peak;
  for (let i = 0; i < samples.length; i += 1) samples[i] *= factor;
}

// One-pole filter coefficient for a cutoff frequency.
export const onePoleCoefficient = (hz: number, sampleRate: number): number =>
  1 - Math.exp((-TWO_PI * hz) / sampleRate);
