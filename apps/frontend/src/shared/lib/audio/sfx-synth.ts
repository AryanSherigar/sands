import { SensoryCueId } from "@/shared/constants/sensory-cues";
import {
  addNoiseBurst,
  addTone,
  bandPass,
  blankSamples,
  fadeEdges,
  noiseSource,
  scaleToPeak,
  TWO_PI,
} from "./synth-primitives";

type CueRenderer = (sampleRate: number) => Float32Array;

const PHONE_LOW_HZ = 440;
const PHONE_HIGH_HZ = 480;
const PHONE_BURST_SECONDS = 0.4;
const PHONE_PAUSE_SECONDS = 0.2;
const PHONE_BURSTS = 3;
const PHONE_LEVEL = 0.35;
const PHONE_FADE_SECONDS = 0.01;
const SILENT_CUE_SECONDS = 0.05;
const PAPER_TOTAL_SECONDS = 0.55;
const PAPER_BURST_STARTS_SECONDS = [0, 0.08, 0.17, 0.29, 0.4];
const PAPER_BURST_SECONDS = 0.07;
const PAPER_LEVEL = 0.28;
const PAPER_NOISE_SEED = 20261026;

const renderPhoneRing: CueRenderer = (sampleRate) => {
  const burstSamples = Math.floor(PHONE_BURST_SECONDS * sampleRate);
  const pauseSamples = Math.floor(PHONE_PAUSE_SECONDS * sampleRate);
  const fadeSamples = Math.max(1, Math.floor(PHONE_FADE_SECONDS * sampleRate));
  const samples = new Float32Array(PHONE_BURSTS * (burstSamples + pauseSamples));
  for (let burst = 0; burst < PHONE_BURSTS; burst += 1) {
    const offset = burst * (burstSamples + pauseSamples);
    for (let i = 0; i < burstSamples; i += 1) {
      const time = i / sampleRate;
      const edge = Math.min(1, i / fadeSamples, (burstSamples - 1 - i) / fadeSamples);
      const tone =
        Math.sin(TWO_PI * PHONE_LOW_HZ * time) +
        Math.sin(TWO_PI * PHONE_HIGH_HZ * time);
      samples[offset + i] = (tone / 2) * PHONE_LEVEL * edge;
    }
  }
  return samples;
};

// Short crackles of high-passed noise (each sample minus the last), each
// fading out, like a sheet of paper being lifted and set down.
const renderPaperRustle: CueRenderer = (sampleRate) => {
  const samples = new Float32Array(Math.floor(PAPER_TOTAL_SECONDS * sampleRate));
  const nextNoise = noiseSource(PAPER_NOISE_SEED);
  const burstSamples = Math.floor(PAPER_BURST_SECONDS * sampleRate);
  let previous = 0;
  for (const startSeconds of PAPER_BURST_STARTS_SECONDS) {
    const offset = Math.floor(startSeconds * sampleRate);
    for (let i = 0; i < burstSamples && offset + i < samples.length; i += 1) {
      const noise = nextNoise();
      const fade = 1 - i / burstSamples;
      samples[offset + i] = ((noise - previous) / 2) * fade * PAPER_LEVEL;
      previous = noise;
    }
  }
  return samples;
};

const KNOCK_STARTS_SECONDS = [0, 0.34, 0.68];
const KNOCK_TOTAL_SECONDS = 1.1;
const KNOCK_LEVEL = 0.8;
const KNOCK_NOISE_SEED = 77;
const KNOCK_THUMP_HZ = 95;
const KNOCK_THUMP_END_HZ = 48;

// Three heavy knocks on a door: a low thump that drops in pitch, plus a dull
// knuckle of muffled noise on the hit.
const renderHeavyKnock: CueRenderer = (sampleRate) => {
  const samples = blankSamples(KNOCK_TOTAL_SECONDS, sampleRate);
  const nextNoise = noiseSource(KNOCK_NOISE_SEED);
  for (const startSeconds of KNOCK_STARTS_SECONDS) {
    addTone(samples, sampleRate, {
      startSeconds,
      durationSeconds: 0.3,
      hz: KNOCK_THUMP_HZ,
      endHz: KNOCK_THUMP_END_HZ,
      level: KNOCK_LEVEL,
      decaySeconds: 0.07,
    });
    addNoiseBurst(samples, sampleRate, nextNoise, {
      startSeconds,
      durationSeconds: 0.05,
      level: 0.5,
      decaySeconds: 0.012,
      smoothing: 0.12,
    });
  }
  scaleToPeak(samples, KNOCK_LEVEL);
  return samples;
};

const BUZZ_SECONDS = 1.4;
const BUZZ_BASE_HZ = 100;
const BUZZ_HARMONIC_LEVELS = [1, 0.5, 0.33];
const BUZZ_FLUTTER_HZ = 9;
const BUZZ_LEVEL = 0.28;

// A failing fluorescent tube: a 100 Hz hum with its harmonics, wavering fast.
const renderLightBuzz: CueRenderer = (sampleRate) => {
  const samples = blankSamples(BUZZ_SECONDS, sampleRate);
  for (let i = 0; i < samples.length; i += 1) {
    const time = i / sampleRate;
    let hum = 0;
    BUZZ_HARMONIC_LEVELS.forEach((level, harmonic) => {
      hum += level * Math.sin(TWO_PI * BUZZ_BASE_HZ * (harmonic + 1) * time);
    });
    const flutter = 0.65 + 0.35 * Math.sin(TWO_PI * BUZZ_FLUTTER_HZ * time);
    samples[i] = hum * flutter;
  }
  fadeEdges(samples, sampleRate, 0.04);
  scaleToPeak(samples, BUZZ_LEVEL);
  return samples;
};

const FOOTSTEP_COUNT = 6;
const FOOTSTEP_INTERVAL_SECONDS = 0.58;
const FOOTSTEP_TOTAL_SECONDS = 3.7;
const FOOTSTEP_LEVEL = 0.3;
const FOOTSTEP_NOISE_SEED = 4242;

// Footsteps far off down a corridor: muffled noise ticks at a walking pace that
// swell slightly as they approach.
const renderDistantFootsteps: CueRenderer = (sampleRate) => {
  const samples = blankSamples(FOOTSTEP_TOTAL_SECONDS, sampleRate);
  const nextNoise = noiseSource(FOOTSTEP_NOISE_SEED);
  for (let step = 0; step < FOOTSTEP_COUNT; step += 1) {
    const approach = 0.55 + (0.45 * step) / (FOOTSTEP_COUNT - 1);
    addNoiseBurst(samples, sampleRate, nextNoise, {
      startSeconds: step * FOOTSTEP_INTERVAL_SECONDS,
      durationSeconds: 0.12,
      level: FOOTSTEP_LEVEL * approach,
      decaySeconds: 0.03,
      smoothing: 0.08,
    });
  }
  fadeEdges(samples, sampleRate);
  return samples;
};

const STATIC_SECONDS = 1.3;
const STATIC_LEVEL = 0.26;
const STATIC_SEED = 909;
const STATIC_LOW_COEFFICIENT = 0.05;
const STATIC_HIGH_COEFFICIENT = 0.55;
const STATIC_WAVER_HZ = 5.5;

// A radio between stations: band-passed noise that swells and drops out.
const renderRadioStatic: CueRenderer = (sampleRate) => {
  const nextNoise = noiseSource(STATIC_SEED);
  const raw = blankSamples(STATIC_SECONDS, sampleRate);
  for (let i = 0; i < raw.length; i += 1) raw[i] = nextNoise();
  const samples = bandPass(raw, STATIC_LOW_COEFFICIENT, STATIC_HIGH_COEFFICIENT);
  for (let i = 0; i < samples.length; i += 1) {
    const waver = 0.6 + 0.4 * Math.sin((TWO_PI * STATIC_WAVER_HZ * i) / sampleRate);
    samples[i] *= waver;
  }
  fadeEdges(samples, sampleRate, 0.03);
  scaleToPeak(samples, STATIC_LEVEL);
  return samples;
};

const CHIME_TOTAL_SECONDS = 1.8;
const CHIME_LEVEL = 0.3;
const CHIME_FIRST_HZ = 880;
const CHIME_SECOND_HZ = 659.25;
const CHIME_SECOND_START_SECONDS = 0.5;

// An elevator arriving: two soft notes, the second one a beat late and lower.
const renderElevatorChime: CueRenderer = (sampleRate) => {
  const samples = blankSamples(CHIME_TOTAL_SECONDS, sampleRate);
  const notes = [
    { startSeconds: 0, hz: CHIME_FIRST_HZ },
    { startSeconds: CHIME_SECOND_START_SECONDS, hz: CHIME_SECOND_HZ },
  ];
  for (const note of notes) {
    addTone(samples, sampleRate, {
      ...note,
      durationSeconds: 1.2,
      level: CHIME_LEVEL,
      decaySeconds: 0.35,
      attackSeconds: 0.012,
    });
  }
  fadeEdges(samples, sampleRate);
  return samples;
};

const CLICK_TOTAL_SECONDS = 0.14;
const CLICK_LEVEL = 0.9;
const CLICK_SEED = 31337;
const CLICK_RESONANCE_HZ = 1800;

// A lamp switch: one sharp click with a small ring, louder than the room.
const renderLampClick: CueRenderer = (sampleRate) => {
  const samples = blankSamples(CLICK_TOTAL_SECONDS, sampleRate);
  addNoiseBurst(samples, sampleRate, noiseSource(CLICK_SEED), {
    startSeconds: 0,
    durationSeconds: 0.01,
    level: 0.9,
    decaySeconds: 0.002,
  });
  addTone(samples, sampleRate, {
    startSeconds: 0,
    durationSeconds: 0.1,
    hz: CLICK_RESONANCE_HZ,
    level: 0.5,
    decaySeconds: 0.018,
    attackSeconds: 0.0005,
  });
  scaleToPeak(samples, CLICK_LEVEL);
  return samples;
};

const TYPING_CLICKS = 16;
const TYPING_SEED = 5150;
const TYPING_MIN_GAP_SECONDS = 0.045;
const TYPING_GAP_SPAN_SECONDS = 0.13;
const TYPING_TOTAL_SECONDS = 2.2;
const TYPING_LEVEL = 0.26;

// Someone typing in the next room: short clicks at uneven gaps, each with a
// slightly different pitch.
const renderKeyboardTyping: CueRenderer = (sampleRate) => {
  const samples = blankSamples(TYPING_TOTAL_SECONDS, sampleRate);
  const nextNoise = noiseSource(TYPING_SEED);
  let startSeconds = 0.02;
  for (let click = 0; click < TYPING_CLICKS; click += 1) {
    const unit = (nextNoise() + 1) / 2;
    addNoiseBurst(samples, sampleRate, nextNoise, {
      startSeconds,
      durationSeconds: 0.012,
      level: TYPING_LEVEL,
      decaySeconds: 0.003,
    });
    addTone(samples, sampleRate, {
      startSeconds,
      durationSeconds: 0.03,
      hz: 1500 + unit * 1200,
      level: TYPING_LEVEL * 0.6,
      decaySeconds: 0.008,
      attackSeconds: 0.0004,
    });
    startSeconds += TYPING_MIN_GAP_SECONDS + unit * TYPING_GAP_SPAN_SECONDS;
  }
  fadeEdges(samples, sampleRate);
  return samples;
};

const renderSilence: CueRenderer = (sampleRate) => blankSamples(SILENT_CUE_SECONDS, sampleRate);

const RENDERERS: Record<SensoryCueId, CueRenderer> = {
  phone_ring: renderPhoneRing,
  heavy_knock: renderHeavyKnock,
  light_buzz: renderLightBuzz,
  distant_footsteps: renderDistantFootsteps,
  // The hard cut is the whole effect, so this one is only dead air.
  sudden_silence: renderSilence,
  radio_static: renderRadioStatic,
  elevator_chime: renderElevatorChime,
  lamp_click: renderLampClick,
  keyboard_typing: renderKeyboardTyping,
  paper_rustle: renderPaperRustle,
};

export function synthesizeCue(
  context: BaseAudioContext,
  cue: SensoryCueId,
): AudioBuffer {
  const samples = RENDERERS[cue](context.sampleRate);
  const buffer = context.createBuffer(1, samples.length, context.sampleRate);
  buffer.getChannelData(0).set(samples);
  return buffer;
}
