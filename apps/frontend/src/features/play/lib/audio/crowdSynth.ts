import {
  TWO_PI,
  bandPass,
  fadeEdges,
  noiseSource,
  onePoleCoefficient,
  scaleToPeak,
} from "@/shared/lib/audio/synth-primitives";
import type { CrowdIntensity, CrowdMood, CrowdReaction } from "../../types/battleSpeech.types";

interface MoodProfile {
  seed: number;
  seconds: number;
  peak: number;
  lowHz: number;
  highHz: number;
  envelope: (progress: number) => number;
}

const MURMUR_WOBBLE_CYCLES = 3;
const MURMUR_WOBBLE_DEPTH = 0.3;
const PROTEST_PULSE_CYCLES = 5;
const CHEER_SWELL_PROGRESS = 0.3;
const CHEER_DECAY_RATE = 3;
const HUSH_DECAY_RATE = 4;

const MOOD_PROFILES: Record<CrowdMood, MoodProfile> = {
  hush: {
    seed: 11,
    seconds: 0.9,
    peak: 0.08,
    lowHz: 200,
    highHz: 800,
    envelope: (progress) => Math.exp(-HUSH_DECAY_RATE * progress),
  },
  murmur: {
    seed: 23,
    seconds: 1.6,
    peak: 0.22,
    lowHz: 300,
    highHz: 1400,
    envelope: (progress) =>
      (1 - MURMUR_WOBBLE_DEPTH + MURMUR_WOBBLE_DEPTH * Math.sin(TWO_PI * MURMUR_WOBBLE_CYCLES * progress)) *
      (1 - progress / 2),
  },
  protest: {
    seed: 37,
    seconds: 2,
    peak: 0.4,
    lowHz: 150,
    highHz: 1000,
    envelope: (progress) =>
      (0.5 + 0.5 * Math.abs(Math.sin(TWO_PI * PROTEST_PULSE_CYCLES * progress))) * (0.6 + 0.4 * progress),
  },
  cheer: {
    seed: 53,
    seconds: 2.4,
    peak: 0.45,
    lowHz: 600,
    highHz: 3200,
    envelope: (progress) =>
      progress < CHEER_SWELL_PROGRESS
        ? progress / CHEER_SWELL_PROGRESS
        : Math.exp(-CHEER_DECAY_RATE * (progress - CHEER_SWELL_PROGRESS)),
  },
};

const INTENSITY_PEAK_SCALE: Record<CrowdIntensity, number> = { 1: 0.55, 2: 0.8, 3: 1 };
const INTENSITY_LENGTH_SCALE: Record<CrowdIntensity, number> = { 1: 0.7, 2: 0.85, 3: 1 };

export function renderCrowdReaction(reaction: CrowdReaction, sampleRate: number): Float32Array {
  const profile = MOOD_PROFILES[reaction.mood];
  const length = Math.floor(profile.seconds * INTENSITY_LENGTH_SCALE[reaction.intensity] * sampleRate);
  const nextNoise = noiseSource(profile.seed);
  const noise = new Float32Array(length);
  for (let i = 0; i < length; i += 1) noise[i] = nextNoise();
  const samples = bandPass(
    noise,
    onePoleCoefficient(profile.lowHz, sampleRate),
    onePoleCoefficient(profile.highHz, sampleRate),
  );
  for (let i = 0; i < length; i += 1) samples[i] *= profile.envelope(i / length);
  scaleToPeak(samples, profile.peak * INTENSITY_PEAK_SCALE[reaction.intensity]);
  fadeEdges(samples, sampleRate);
  return samples;
}
