import { describe, expect, it } from "vitest";
import {
  nextWhisperDelayMs,
  synthesizeWhisper,
  WHISPER_DELAY_SPAN_MS,
  WHISPER_MIN_DELAY_MS,
} from "../phantom-whispers";
import { seededRandom } from "../synth-primitives";
import { FakeAudioContext } from "./fakeAudioContext";

const whisper = (seed: string) =>
  synthesizeWhisper(new FakeAudioContext() as unknown as BaseAudioContext, seededRandom(seed));

describe("nextWhisperDelayMs", () => {
  it("stays between 20 and 60 seconds", () => {
    const random = seededRandom("delays");
    for (let i = 0; i < 500; i += 1) {
      const delay = nextWhisperDelayMs(random);
      expect(delay).toBeGreaterThanOrEqual(WHISPER_MIN_DELAY_MS);
      expect(delay).toBeLessThan(WHISPER_MIN_DELAY_MS + WHISPER_DELAY_SPAN_MS);
    }
  });

  it("repeats for the same seed and differs between seeds", () => {
    expect(nextWhisperDelayMs(seededRandom("a"))).toBe(nextWhisperDelayMs(seededRandom("a")));
    expect(nextWhisperDelayMs(seededRandom("a"))).not.toBe(nextWhisperDelayMs(seededRandom("b")));
  });
});

describe("synthesizeWhisper", () => {
  it("is deterministic for a seed", () => {
    expect(Array.from(whisper("pt").getChannelData(0))).toEqual(
      Array.from(whisper("pt").getChannelData(0)),
    );
  });

  it("is a breath-length sound normalised to full scale", () => {
    const buffer = whisper("pt");
    const data = buffer.getChannelData(0);
    const peak = data.reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);

    expect(buffer.duration).toBeGreaterThanOrEqual(1);
    expect(buffer.duration).toBeLessThan(2);
    expect(peak).toBeCloseTo(1, 5);
    expect(Array.from(data).every(Number.isFinite)).toBe(true);
  });

  it("swells in and out instead of starting or ending abruptly", () => {
    const data = whisper("pt").getChannelData(0);

    expect(Math.abs(data[0])).toBeLessThan(0.01);
    expect(Math.abs(data[data.length - 1])).toBeLessThan(0.01);
  });
});
