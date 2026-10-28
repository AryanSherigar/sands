import { describe, expect, it } from "vitest";
import { MAX_VIGNETTE_STRENGTH, tensionVignetteStrength } from "./tensionVignette";

describe("tensionVignetteStrength", () => {
  it("is zero at the first tier and the maximum at the last", () => {
    expect(tensionVignetteStrength(0, 4)).toBe(0);
    expect(tensionVignetteStrength(3, 4)).toBeCloseTo(MAX_VIGNETTE_STRENGTH);
  });

  it("scales linearly in between", () => {
    expect(tensionVignetteStrength(1, 4)).toBeCloseTo(MAX_VIGNETTE_STRENGTH / 3);
    expect(tensionVignetteStrength(2, 4)).toBeCloseTo((MAX_VIGNETTE_STRENGTH * 2) / 3);
  });

  it("is zero for a single-tier field", () => {
    expect(tensionVignetteStrength(0, 1)).toBe(0);
  });
});
