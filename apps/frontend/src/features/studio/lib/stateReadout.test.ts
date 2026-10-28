import { describe, expect, it } from "vitest";
import type { ValueOption } from "../types/sentence.types";
import { buildReadoutRows, listHiddenPaths, readStateValue } from "./stateReadout";

const OPTIONS: ValueOption[] = [
  { path: "lantern_oil", label: "Lantern oil", kind: "number", source: "tracked" },
  { path: "has_escaped", label: "Has escaped", kind: "boolean", source: "tracked" },
  { path: "player.health", label: "Health", kind: "number", source: "tracked" },
  { path: "sanity", label: "Sanity", kind: "number", source: "tracked" },
  { path: "mara-id.trust", label: "Mara's Trust", kind: "number", source: "card" },
];

describe("stateReadout", () => {
  it("reads flat, dotted and card values", () => {
    const state = { lantern_oil: 3, player: { health: 7 }, entities: { "mara-id": { trust: 5 } } };
    expect(readStateValue(state, "lantern_oil")).toBe(3);
    expect(readStateValue(state, "player.health")).toBe(7);
    expect(readStateValue(state, "mara-id.trust")).toBe(5);
    expect(readStateValue(state, "missing")).toBeUndefined();
  });

  it("lists hidden fields and everything inside a hidden group", () => {
    const hidden = listHiddenPaths({
      sanity: { type: "number", hidden: true },
      seed: { type: "object", hidden: true, fields: { rule: { type: "enum" } } },
      shown: { type: "number" },
    });
    expect([...hidden].sort()).toEqual(["sanity", "seed", "seed.rule"]);
  });

  it("builds plain rows, with yes or no, and marks hidden values without leaking them", () => {
    const rows = buildReadoutRows(
      OPTIONS,
      { lantern_oil: 3, has_escaped: false, sanity: 2, entities: { "mara-id": { trust: 9 } } },
      new Set(["sanity"]),
    );
    expect(rows.map((row) => `${row.label}: ${row.text}`)).toEqual([
      "Lantern oil: 3",
      "Has escaped: no",
      "Sanity: hidden from players",
      "Mara's Trust: 9",
    ]);
  });
});
