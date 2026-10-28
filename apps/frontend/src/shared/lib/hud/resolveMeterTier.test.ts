import { describe, expect, it } from "vitest";
import { resolveMeterTier } from "./resolveMeterTier";

const tiers = [
  { name: "clear", min: 75 },
  { name: "frayed", min: 50 },
  { name: "paranoid", min: 25 },
  { name: "unraveling" },
];

describe("resolveMeterTier", () => {
  it.each([
    [100, "clear"],
    [75, "clear"],
    [74, "frayed"],
    [25, "paranoid"],
    [24, "unraveling"],
    [-8, "unraveling"],
  ])("maps %i to %s", (value, name) => {
    expect(resolveMeterTier(tiers, value)).toBe(name);
  });

  it("returns null without tiers", () => {
    expect(resolveMeterTier(undefined, 10)).toBeNull();
    expect(resolveMeterTier([], 10)).toBeNull();
  });
});
