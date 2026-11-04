import { describe, expect, it } from "vitest";
import { renderCrowdReaction } from "../crowdSynth";

const SAMPLE_RATE = 8000;
const MOODS = ["hush", "murmur", "protest", "cheer"] as const;

const peakOf = (samples: Float32Array): number =>
  samples.reduce((max, sample) => Math.max(max, Math.abs(sample)), 0);

describe("renderCrowdReaction", () => {
  it("renders the same samples every time for the same reaction", () => {
    const first = renderCrowdReaction({ mood: "cheer", intensity: 2 }, SAMPLE_RATE);
    const second = renderCrowdReaction({ mood: "cheer", intensity: 2 }, SAMPLE_RATE);
    expect(Array.from(first)).toEqual(Array.from(second));
  });

  it.each(MOODS)("keeps %s audible but never clipping", (mood) => {
    const samples = renderCrowdReaction({ mood, intensity: 3 }, SAMPLE_RATE);
    const peak = peakOf(samples);
    expect(peak).toBeGreaterThan(0.01);
    expect(peak).toBeLessThanOrEqual(1);
    expect(samples.every(Number.isFinite)).toBe(true);
  });

  it("makes a stronger reaction louder and longer", () => {
    const soft = renderCrowdReaction({ mood: "cheer", intensity: 1 }, SAMPLE_RATE);
    const strong = renderCrowdReaction({ mood: "cheer", intensity: 3 }, SAMPLE_RATE);
    expect(peakOf(strong)).toBeGreaterThan(peakOf(soft));
    expect(strong.length).toBeGreaterThan(soft.length);
  });

  it("keeps a hush quieter than a murmur and a murmur quieter than a protest", () => {
    const peak = (mood: (typeof MOODS)[number]) =>
      peakOf(renderCrowdReaction({ mood, intensity: 2 }, SAMPLE_RATE));
    expect(peak("hush")).toBeLessThan(peak("murmur"));
    expect(peak("murmur")).toBeLessThan(peak("protest"));
  });

  it("sounds different for each mood", () => {
    const rendered = MOODS.map((mood) =>
      Array.from(renderCrowdReaction({ mood, intensity: 2 }, SAMPLE_RATE).slice(0, 400)).join(","),
    );
    expect(new Set(rendered).size).toBe(MOODS.length);
  });
});
