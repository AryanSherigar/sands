import { describe, expect, it } from "vitest";
import { seededUnit } from "./seededUnit";

describe("seededUnit", () => {
  it("returns the same value for the same inputs", () => {
    expect(seededUnit("pt-1", 42)).toBe(seededUnit("pt-1", 42));
  });

  it("varies with the seed and with the number", () => {
    expect(seededUnit("pt-1", 42)).not.toBe(seededUnit("pt-2", 42));
    expect(seededUnit("pt-1", 42)).not.toBe(seededUnit("pt-1", 43));
  });

  it("stays inside [0, 1) and spreads roughly evenly", () => {
    const draws = Array.from({ length: 2000 }, (_, i) => seededUnit("pt", i));
    expect(draws.every((draw) => draw >= 0 && draw < 1)).toBe(true);
    const belowHalf = draws.filter((draw) => draw < 0.5).length;
    expect(belowHalf).toBeGreaterThan(850);
    expect(belowHalf).toBeLessThan(1150);
  });
});
