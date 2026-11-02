import { describe, expect, it } from "vitest";
import {
  calculateExchangeDots,
  deriveLeaderMoodTag,
  generateHeraldicCrestSvg,
} from "../negotiationStance.utils";

describe("negotiationStance.utils", () => {
  it("derives mood tag from traits and war status", () => {
    expect(deriveLeaderMoodTag(["cautious", "proud"], true)).toBe("Guarded — Distrustful");
    expect(deriveLeaderMoodTag(["bellicose"], true)).toBe("Unyielding — Hostile");
    expect(deriveLeaderMoodTag(["pragmatic"], false)).toBe("Calculating — Attentive");
    expect(deriveLeaderMoodTag([], false)).toBe("Measured — Reserved");
  });

  it("calculates exchange dot array correctly", () => {
    const result = calculateExchangeDots(3, 6);
    expect(result.usedCount).toBe(3);
    expect(result.totalCap).toBe(6);
    expect(result.activeDots).toEqual([true, true, true, false, false, false]);
  });

  it("generates inline heraldic crest SVG for missing portraits", () => {
    const svg = generateHeraldicCrestSvg("Valdren", "#46606E");
    expect(svg).toContain("<svg");
    expect(svg).toContain("%2346606E");
    expect(svg).toContain("V");
  });

  it("keeps the crest URI free of raw fragment characters", () => {
    expect(generateHeraldicCrestSvg("Valdren").includes("#")).toBe(false);
  });
});
