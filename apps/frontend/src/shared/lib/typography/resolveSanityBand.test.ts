import { describe, expect, it } from "vitest";
import { resolveSanityBand } from "./resolveSanityBand";

const effects = { moderate_below: 50, critical_below: 25 };

describe("resolveSanityBand", () => {
  it.each([
    [100, "none"],
    [50, "none"],
    [49, "moderate"],
    [25, "moderate"],
    [24, "critical"],
    [0, "critical"],
    [-42, "critical"],
  ])("maps %i to %s", (value, band) => {
    expect(resolveSanityBand(value, effects)).toBe(band);
  });

  it("is none without effects", () => {
    expect(resolveSanityBand(0, undefined)).toBe("none");
  });

  it("ignores a threshold the creator left out", () => {
    expect(resolveSanityBand(10, { moderate_below: 50 })).toBe("moderate");
    expect(resolveSanityBand(10, { critical_below: 25 })).toBe("critical");
    expect(resolveSanityBand(60, { critical_below: 25 })).toBe("none");
  });
});
