import { describe, expect, it } from "vitest";
import { describeEdictEffects } from "../edictEffects";

describe("describeEdictEffects", () => {
  it("words each ongoing effect with its sign", () => {
    expect(
      describeEdictEffects({ manpower_regen_percent: 25, unrest_per_turn: -5, tax_percent_points: 15, trade_efficiency_percent: -10 }),
    ).toEqual(["+25% manpower regrowth", "-5 unrest each turn", "+15 points of tax", "-10% trade income"]);
  });

  it("skips unknown keys, zero effects and a missing record", () => {
    expect(describeEdictEffects({ mystery: 3, unrest_per_turn: 0 })).toEqual([]);
    expect(describeEdictEffects(undefined)).toEqual([]);
  });
});
