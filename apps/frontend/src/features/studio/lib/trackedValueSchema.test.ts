import { describe, expect, it } from "vitest";
import { buildStateField, buildValueKey } from "./trackedValueSchema";

describe("buildValueKey", () => {
  it("turns a name into a key", () => {
    expect(buildValueKey("Lantern oil!", new Set())).toBe("lantern_oil");
  });

  it("avoids taken and reserved keys", () => {
    expect(buildValueKey("Oil", new Set(["oil"]))).toBe("oil_2");
    expect(buildValueKey("Entities", new Set())).toBe("entities_2");
  });

  it("falls back when the name has no letters or digits", () => {
    expect(buildValueKey("???", new Set())).toBe("value");
  });
});

describe("buildStateField", () => {
  it("builds a number with its range and start", () => {
    expect(buildStateField({ name: " Health ", kind: "number", min: 0, max: 10, initial: 10 })).toEqual({
      type: "number",
      label: "Health",
      initial: 10,
      min: 0,
      max: 10,
    });
  });

  it("starts a yes/no at no and a choice at its first option", () => {
    expect(buildStateField({ name: "Has key", kind: "boolean" }).initial).toBe(false);
    expect(buildStateField({ name: "Time", kind: "enum", options: ["Dawn", "Day"] })).toMatchObject({
      type: "enum",
      initial: "Dawn",
      options: ["Dawn", "Day"],
    });
  });

  it("keeps the meaning line and the display hint when given", () => {
    const display = { kind: "meter" };
    expect(buildStateField({ name: "Trust", kind: "number", description: "Mara's trust", display })).toMatchObject({
      description: "Mara's trust",
      display,
    });
  });
});
