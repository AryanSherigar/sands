import { describe, expect, it } from "vitest";
import type { Sentence, ValueOption } from "../types/sentence.types";
import { listCardValueLabels, overridesForSentence } from "./stateOverrides";

const OPTIONS: ValueOption[] = [
  { path: "lantern_oil", label: "Lantern oil", kind: "number", min: 0, max: 10, source: "tracked" },
  { path: "has_key", label: "Has the key", kind: "boolean", source: "tracked" },
  { path: "time", label: "Time", kind: "enum", options: ["Dawn", "Night"], source: "tracked" },
  { path: "player.health", label: "Health", kind: "number", min: 0, max: 5, source: "tracked" },
  { path: "mara-id.trust", label: "Mara's Trust", kind: "number", min: 0, max: 10, source: "card" },
];

const sentence = (rows: Sentence["rows"], joiner: Sentence["joiner"] = "and"): Sentence => ({ rows, joiner });

describe("overridesForSentence", () => {
  it.each([
    ["drops_to uses the amount", { path: "lantern_oil", comparison: "drops_to", amount: 2 }, 2],
    ["at_most uses the amount", { path: "lantern_oil", comparison: "at_most", amount: 3 }, 3],
    ["drops_to without an amount uses the lowest", { path: "lantern_oil", comparison: "drops_to" }, 0],
    ["rises_to uses the amount", { path: "lantern_oil", comparison: "rises_to", amount: 8 }, 8],
    ["at_least uses the amount", { path: "lantern_oil", comparison: "at_least", amount: 7 }, 7],
    ["at_least without an amount uses the highest", { path: "lantern_oil", comparison: "at_least" }, 10],
    ["exactly uses the amount", { path: "lantern_oil", comparison: "exactly", amount: 4 }, 4],
    ["becomes_yes is true", { path: "has_key", comparison: "becomes_yes" }, true],
    ["becomes_no is false", { path: "has_key", comparison: "becomes_no" }, false],
    ["becomes_option is the option", { path: "time", comparison: "becomes_option", amount: "Night" }, "Night"],
  ] as const)("%s", (_name, row, expected) => {
    const overrides = overridesForSentence(sentence([{ ...row }]), OPTIONS);
    expect(overrides).toEqual({ [row.path]: expected });
  });

  it("presets every row of an and sentence, including dotted paths", () => {
    const overrides = overridesForSentence(
      sentence([
        { path: "lantern_oil", comparison: "at_most", amount: 2 },
        { path: "player.health", comparison: "drops_to", amount: 0 },
        { path: "has_key", comparison: "becomes_yes" },
      ]),
      OPTIONS,
    );
    expect(overrides).toEqual({ lantern_oil: 2, "player.health": 0, has_key: true });
  });

  it("presets only the first row of an or sentence", () => {
    const overrides = overridesForSentence(
      sentence(
        [
          { path: "lantern_oil", comparison: "at_most", amount: 2 },
          { path: "has_key", comparison: "becomes_yes" },
        ],
        "or",
      ),
      OPTIONS,
    );
    expect(overrides).toEqual({ lantern_oil: 2 });
  });

  it("presets the first row an or sentence can preset, skipping card and value-against-value rows", () => {
    const rows: Sentence["rows"] = [
      { path: "mara-id.trust", comparison: "at_least", amount: 8 },
      { path: "lantern_oil", comparison: "at_most", ref: "player.health" },
      { path: "has_key", comparison: "becomes_yes" },
      { path: "lantern_oil", comparison: "at_most", amount: 2 },
    ];
    expect(overridesForSentence(sentence(rows, "or"), OPTIONS)).toEqual({ has_key: true });
    expect(listCardValueLabels(sentence(rows, "or"), OPTIONS)).toEqual(["Mara's Trust"]);
  });

  it("presets nothing for an or sentence with no presettable row", () => {
    const rows: Sentence["rows"] = [{ path: "mara-id.trust", comparison: "at_least", amount: 8 }];
    expect(overridesForSentence(sentence(rows, "or"), OPTIONS)).toEqual({});
  });

  it("leaves out card values and value-against-value rows", () => {
    const rows: Sentence["rows"] = [
      { path: "mara-id.trust", comparison: "at_least", amount: 8 },
      { path: "lantern_oil", comparison: "at_most", ref: "player.health" },
    ];
    expect(overridesForSentence(sentence(rows), OPTIONS)).toEqual({});
    expect(listCardValueLabels(sentence(rows), OPTIONS)).toEqual(["Mara's Trust"]);
  });
});
