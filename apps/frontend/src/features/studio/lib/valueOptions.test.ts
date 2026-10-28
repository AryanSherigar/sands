import { describe, expect, it } from "vitest";
import { buildEntityFixture, buildFactFixture } from "../test/cardApiMock";
import { buildConditionFixture, buildEndConditionFixture, buildInvariantFixture } from "../test/studioApiMock";
import type { StateFieldDefinition } from "../types/scenario.types";
import {
  buildUnsupportedPathCheck,
  buildValueOptions,
  countValueUsages,
  extractFieldPaths,
  findLinkUsages,
  findValueUsages,
  humanizeKey,
  listTrackedValueOptions,
} from "./valueOptions";

const schema: Record<string, StateFieldDefinition> = {
  lantern_oil: { type: "number", label: "Lantern oil", min: 0, max: 10, initial: 10 },
  has_key: { type: "boolean" },
  time: { type: "enum", options: ["Dawn", { value: "Day" }, "Night"] },
  note: { type: "string" },
  tags: { type: "list" },
  mood: { type: "derived", formula: "x" },
  player: { type: "object", fields: { health: { type: "number", label: "Health" } } },
};

describe("listTrackedValueOptions", () => {
  it("keeps number, yes/no and choice values only, in plain words", () => {
    const options = listTrackedValueOptions(schema);
    expect(options.map((option) => [option.path, option.label, option.kind])).toEqual([
      ["lantern_oil", "Lantern oil", "number"],
      ["has_key", "Has key", "boolean"],
      ["time", "Time", "enum"],
      ["player.health", "Health", "number"],
    ]);
  });

  it("carries the range and the choices", () => {
    const [oil, , time] = listTrackedValueOptions(schema);
    expect(oil).toMatchObject({ min: 0, max: 10, source: "tracked" });
    expect(time.options).toEqual(["Dawn", "Day", "Night"]);
  });
});

describe("buildValueOptions", () => {
  it("adds card values labelled with the card's name", () => {
    const guard = buildEntityFixture({
      entity_id: "guard-1",
      canonical_name: "Guard",
      attributes_schema: {
        health: { type: "number", min: 0, max: 5 },
        name_tag: { type: "string" },
        awake: { type: "boolean", label: "Awake" },
      },
    });
    const options = buildValueOptions({}, [guard]);
    expect(options.map((option) => [option.path, option.label, option.source])).toEqual([
      ["guard-1.health", "Guard's Health", "card"],
      ["guard-1.awake", "Guard's Awake", "card"],
    ]);
  });
});

describe("extractFieldPaths", () => {
  it("reads field and ref through AND, OR and NOT", () => {
    const expression = {
      field: "a",
      op: "<=",
      ref: "max_a",
      AND: { field: "b", op: "==", value: true, OR: { NOT: { field: "c", op: "==", value: 1 } } },
    };
    expect([...extractFieldPaths(expression)].sort()).toEqual(["a", "b", "c", "max_a"]);
  });

  it("is empty for a missing expression", () => {
    expect(extractFieldPaths(null).size).toBe(0);
    expect(extractFieldPaths({}).size).toBe(0);
  });
});

describe("findValueUsages", () => {
  const rows = {
    endConditions: [
      buildEndConditionFixture({
        end_condition_id: "e1",
        condition_expression: { field: "lantern_oil", op: "<=", value: 0 },
      }),
      buildEndConditionFixture({ end_condition_id: "e2", condition_expression: { field: "x", op: "==", value: 1 } }),
    ],
    conditions: [
      buildConditionFixture({
        condition_id: "c1",
        condition_expression: { field: "x", op: "==", value: 1 },
        state_mutations: [{ path: "lantern_oil", op: "decrement", value: 1 }],
      }),
    ],
    invariants: [
      buildInvariantFixture({
        invariant_id: "i1",
        invariant_expression: { field: "y", op: "==", value: 1, OR: { NOT: { field: "lantern_oil", op: "==", value: 2 } } },
      }),
    ],
  };
  const facts = [
    buildFactFixture({
      fact_id: "f1",
      subject_entity_id: "a",
      predicate: "knows",
      object_entity_id: "b",
      when_active: { field: "lantern_oil", op: ">=", value: 2, AND: { field: "x", op: "==", value: 1 } },
    }),
    buildFactFixture({ fact_id: "f2", subject_entity_id: "a", predicate: "knows", object_entity_id: "b" }),
  ];

  it("finds endings, rules (including value changes) and hard limits", () => {
    const usages = findValueUsages("lantern_oil", rows);
    expect(usages.endings.map((row) => row.end_condition_id)).toEqual(["e1"]);
    expect(usages.rules.map((row) => row.condition_id)).toEqual(["c1"]);
    expect(usages.limits.map((row) => row.invariant_id)).toEqual(["i1"]);
    expect(countValueUsages(usages)).toBe(3);
  });

  it("finds the links that only apply while the value matches", () => {
    expect(findLinkUsages("lantern_oil", facts).map((fact) => fact.fact_id)).toEqual(["f1"]);
    expect(findLinkUsages("unused", facts)).toEqual([]);
  });

  it("finds nothing for an unused value", () => {
    expect(countValueUsages(findValueUsages("unused", rows))).toBe(0);
  });
});

describe("humanizeKey", () => {
  it("turns a key into words", () => {
    expect(humanizeKey("has_the_key")).toBe("Has the key");
  });
});

describe("buildUnsupportedPathCheck", () => {
  const guard = buildEntityFixture({
    entity_id: "guard-1",
    canonical_name: "Guard",
    attributes_schema: { health: { type: "number" }, mood: { type: "string" } },
  });
  const isUnsupported = buildUnsupportedPathCheck(schema, [guard], buildValueOptions(schema, [guard]));

  it("flags paths that exist but the builder cannot show", () => {
    expect(["note", "tags", "mood", "guard-1.mood", "current_location_id", "rule_flags.alarm"].map(isUnsupported)).toEqual(
      [true, true, true, true, true, true],
    );
  });

  it("leaves supported and nonexistent paths alone", () => {
    expect(["lantern_oil", "player.health", "guard-1.health", "gone_value", ""].map(isUnsupported)).toEqual([
      false,
      false,
      false,
      false,
      false,
    ]);
  });
});
