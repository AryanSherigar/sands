import { describe, expect, it } from "vitest";
import { processPhoneEcho, renderBreathing } from "../phone-echo";

const RATE = 8000;

const tone = (seconds: number, hz: number): Float32Array => {
  const samples = new Float32Array(Math.round(seconds * RATE));
  for (let i = 0; i < samples.length; i++) {
    samples[i] = 0.8 * Math.sin((2 * Math.PI * hz * i) / RATE);
  }
  return samples;
};

const peak = (data: Float32Array): number =>
  data.reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);

const energy = (data: Float32Array): number =>
  data.reduce((sum, sample) => sum + sample * sample, 0) / data.length;

describe("processPhoneEcho", () => {
  it("comes back slower than the voice went in", () => {
    const voice = tone(1, 440);
    expect(processPhoneEcho(voice, RATE).length).toBeGreaterThan(voice.length);
  });

  it("never clips", () => {
    expect(peak(processPhoneEcho(tone(1, 440), RATE))).toBeLessThanOrEqual(0.9);
  });

  it("thins out a deep rumble more than a voice-band tone", () => {
    const rumble = energy(processPhoneEcho(tone(1, 60), RATE));
    const voiceBand = energy(processPhoneEcho(tone(1, 800), RATE));
    expect(rumble).toBeLessThan(voiceBand);
  });

  it("is deterministic", () => {
    const voice = tone(0.5, 440);
    expect(Array.from(processPhoneEcho(voice, RATE))).toEqual(
      Array.from(processPhoneEcho(voice, RATE)),
    );
  });

  it("returns silence for silence plus faint hiss only", () => {
    expect(peak(processPhoneEcho(new Float32Array(RATE), RATE))).toBeLessThan(0.05);
  });
});

describe("renderBreathing", () => {
  it("lasts the asked duration and stays quiet", () => {
    const breathing = renderBreathing(RATE, 2000);
    expect(breathing.length).toBe(2 * RATE);
    expect(peak(breathing)).toBeGreaterThan(0.01);
    expect(peak(breathing)).toBeLessThanOrEqual(0.5);
  });
});
