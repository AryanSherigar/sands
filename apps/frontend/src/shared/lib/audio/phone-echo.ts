// Turns a recorded voice into what comes back down a bad line: slower and
// lower, telephone-thin, one slice reversed, a second copy a beat late, hiss.
// Pure sample math (like sfx-synth.ts) so it is deterministic and testable.

const BAND_LOW_HZ = 300;
const BAND_HIGH_HZ = 3400;
const PLAYBACK_RATE = 0.88;
const REVERSED_SLICE_MS = 400;
const DOUBLE_DELAY_MS = 75;
const DOUBLE_GAIN_DB = -9;
const HISS_GAIN = 0.015;
const PEAK_LIMIT = 0.9;
const BREATH_HZ = 0.25;
const BREATH_GAIN = 0.35;
const BREATH_LOWPASS_HZ = 600;
const NOISE_SEED = 1013904223;

function noiseSource(): () => number {
  let state = NOISE_SEED;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 0xffffffff - 0.5;
  };
}

function reverseMiddleSlice(samples: Float32Array, sampleRate: number): Float32Array {
  const out = samples.slice();
  const width = Math.min(out.length, Math.round((REVERSED_SLICE_MS / 1000) * sampleRate));
  const start = Math.floor((out.length - width) / 2);
  out.subarray(start, start + width).reverse();
  return out;
}

function slowDown(samples: Float32Array): Float32Array {
  const out = new Float32Array(Math.floor(samples.length / PLAYBACK_RATE));
  for (let i = 0; i < out.length; i++) {
    const position = i * PLAYBACK_RATE;
    const index = Math.floor(position);
    const next = samples[Math.min(index + 1, samples.length - 1)] ?? 0;
    const fraction = position - index;
    out[i] = (samples[index] ?? 0) * (1 - fraction) + next * fraction;
  }
  return out;
}

function lowPass(samples: Float32Array, sampleRate: number, cutoffHz: number): Float32Array {
  const alpha = 1 - Math.exp((-2 * Math.PI * cutoffHz) / sampleRate);
  const out = new Float32Array(samples.length);
  let previous = 0;
  for (let i = 0; i < samples.length; i++) {
    previous += alpha * (samples[i] - previous);
    out[i] = previous;
  }
  return out;
}

function bandPass(samples: Float32Array, sampleRate: number): Float32Array {
  const lows = lowPass(samples, sampleRate, BAND_LOW_HZ);
  const highPassed = samples.map((sample, i) => sample - lows[i]);
  return lowPass(highPassed, sampleRate, Math.min(BAND_HIGH_HZ, sampleRate / 2 - 1));
}

function withLateDouble(samples: Float32Array, sampleRate: number): Float32Array {
  const delay = Math.round((DOUBLE_DELAY_MS / 1000) * sampleRate);
  const gain = 10 ** (DOUBLE_GAIN_DB / 20);
  const out = new Float32Array(samples.length + delay);
  out.set(samples);
  for (let i = 0; i < samples.length; i++) out[i + delay] += samples[i] * gain;
  return out;
}

function withHissAndLimit(samples: Float32Array): Float32Array {
  const noise = noiseSource();
  const out = samples.map((sample) => sample + noise() * HISS_GAIN);
  const peak = out.reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);
  return peak > PEAK_LIMIT ? out.map((sample) => (sample / peak) * PEAK_LIMIT) : out;
}

export function processPhoneEcho(voice: Float32Array, sampleRate: number): Float32Array {
  const reversed = reverseMiddleSlice(voice, sampleRate);
  const thin = bandPass(slowDown(reversed), sampleRate);
  return withHissAndLimit(withLateDouble(thin, sampleRate));
}

/** What the line carries when there is no voice to send back. */
export function renderBreathing(sampleRate: number, durationMs: number): Float32Array {
  const length = Math.round((durationMs / 1000) * sampleRate);
  const noise = noiseSource();
  const raw = new Float32Array(length).map(() => noise());
  const soft = lowPass(raw, sampleRate, BREATH_LOWPASS_HZ);
  return soft.map((sample, i) => {
    const envelope = 0.5 - 0.5 * Math.cos((2 * Math.PI * BREATH_HZ * i) / sampleRate);
    return Math.max(-BREATH_GAIN, Math.min(BREATH_GAIN, sample * 4 * envelope));
  });
}
