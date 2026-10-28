import { describe, expect, it } from "vitest";
import { getStateValue, readDisplayHints } from "./readDisplayHints";

const clock = {
  type: "number",
  display: { kind: "clock", label: "Shift", start: "23:00", format: "12h" },
};
const meter = {
  type: "number",
  display: { kind: "meter", label: "Sanity", clamp_min: 0, clamp_max: 100 },
};
const tier = {
  type: "enum",
  display: { kind: "tier", label: "Tension" },
};

describe("readDisplayHints", () => {
  it("returns no hints for a plain schema", () => {
    expect(readDisplayHints({ gold: { type: "number" } })).toEqual({ meters: [] });
  });

  it("finds the clock, the meters and the tier with their paths", () => {
    const hints = readDisplayHints({
      shift_minutes: clock,
      sanity: meter,
      battery: meter,
      tension_tier: tier,
    });

    expect(hints.clock?.path).toBe("shift_minutes");
    expect(hints.clock?.hint.start).toBe("23:00");
    expect(hints.meters.map((m) => m.path)).toEqual(["sanity", "battery"]);
    expect(hints.tier?.path).toBe("tension_tier");
  });

  it("finds hints inside object fields by dotted path", () => {
    const hints = readDisplayHints({
      player: { type: "object", fields: { sanity: meter } },
    });

    expect(hints.meters[0].path).toBe("player.sanity");
  });

  it("ignores an unknown hint kind and malformed hints", () => {
    const hints = readDisplayHints({
      a: { type: "number", display: { kind: "gauge" } },
      b: { type: "number", display: "clock" },
      c: null,
    });

    expect(hints).toEqual({ meters: [] });
  });
});

describe("getStateValue", () => {
  it("reads a top-level and a nested value by dotted path", () => {
    const state = { clock: 30, player: { sanity: 12 } };

    expect(getStateValue(state, "clock")).toBe(30);
    expect(getStateValue(state, "player.sanity")).toBe(12);
  });

  it("returns undefined for a missing path", () => {
    expect(getStateValue({ a: 1 }, "b.c")).toBeUndefined();
    expect(getStateValue({ a: 1 }, "a.b")).toBeUndefined();
  });
});
