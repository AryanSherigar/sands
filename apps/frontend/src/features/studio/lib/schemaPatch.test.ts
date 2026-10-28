import { describe, expect, it } from "vitest";
import { patchFieldAtPath } from "./schemaPatch";
import type { StateFieldDefinition } from "../types/scenario.types";

const schema: Record<string, StateFieldDefinition> = {
  sanity: { type: "number", initial: 85 },
  seed: { type: "object", fields: { rule: { type: "enum", options: ["a", "b"] } } },
};

describe("patchFieldAtPath", () => {
  it("merges into a top-level field without touching the others", () => {
    const next = patchFieldAtPath(schema, "sanity", { hidden: true });

    expect(next.sanity).toEqual({ type: "number", initial: 85, hidden: true });
    expect(next.seed).toBe(schema.seed);
  });

  it("reaches into nested fields and removes keys patched to undefined", () => {
    const hidden = patchFieldAtPath(schema, "seed.rule", { initial_random: ["a"] });
    const cleared = patchFieldAtPath(hidden, "seed.rule", { initial_random: undefined });

    expect(hidden.seed.fields!.rule.initial_random).toEqual(["a"]);
    expect("initial_random" in cleared.seed.fields!.rule).toBe(false);
  });

  it("returns the schema unchanged for an unknown path", () => {
    expect(patchFieldAtPath(schema, "nope.x", { hidden: true })).toBe(schema);
  });
});
