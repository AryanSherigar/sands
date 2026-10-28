import { describe, expect, it } from "vitest";
import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import { COMPARISON_OPERATORS } from "../constants/comparisons";
import type { Comparison, Sentence, SentenceRow } from "../types/sentence.types";
import {
  buildSentenceMetadata,
  compileSentence,
  compileWhileLimit,
  describeSentence,
  parseExpression,
  parseWhileLimit,
} from "./sentenceCompiler";

type State = Record<string, unknown>;

const evaluateLeaf = (node: FieldExpression, state: State): boolean => {
  const actual = state[node.field];
  const expected = node.ref === undefined ? node.value : state[node.ref];
  const toNumber = (value: unknown): number => Number(value);
  switch (node.op) {
    case "==":
      return actual === expected;
    case "<=":
      return toNumber(actual) <= toNumber(expected);
    case ">=":
      return toNumber(actual) >= toNumber(expected);
    default:
      return false;
  }
};

// Test-only port of apps/turn-resolution-service/app/turn/expression_evaluator.py
const evaluate = (node: Record<string, unknown> | undefined, state: State): boolean => {
  if (!node) return false;
  const result = "field" in node ? evaluateLeaf(node as unknown as FieldExpression, state) : null;
  const connectives = ["AND", "OR", "NOT"].filter((key) => key in node);
  if (connectives.length > 1) throw new Error("at most one connective");
  if (connectives.length === 0) return result ?? false;
  const connective = connectives[0];
  const sub = evaluate(node[connective] as Record<string, unknown>, state);
  if (connective === "OR") return result === null ? sub : result || sub;
  const operand = connective === "NOT" ? !sub : sub;
  return result === null ? operand : result && operand;
};

const ROW_TABLE: Array<[Comparison, SentenceRow, string, string | number | boolean]> = [
  ["drops_to", { path: "oil", comparison: "drops_to", amount: 2 }, "<=", 2],
  ["rises_to", { path: "oil", comparison: "rises_to", amount: 8 }, ">=", 8],
  ["at_least", { path: "oil", comparison: "at_least", amount: 3 }, ">=", 3],
  ["at_most", { path: "oil", comparison: "at_most", amount: 4 }, "<=", 4],
  ["exactly", { path: "oil", comparison: "exactly", amount: 5 }, "==", 5],
  ["becomes_yes", { path: "has_key", comparison: "becomes_yes" }, "==", true],
  ["becomes_no", { path: "has_key", comparison: "becomes_no" }, "==", false],
  ["becomes_option", { path: "time", comparison: "becomes_option", amount: "Night" }, "==", "Night"],
];

const rowA: SentenceRow = { path: "oil", comparison: "at_most", amount: 2 };
const rowB: SentenceRow = { path: "has_key", comparison: "becomes_yes" };
const rowC: SentenceRow = { path: "time", comparison: "becomes_option", amount: "Night" };

describe("compileSentence", () => {
  it.each(ROW_TABLE)("compiles %s to the listed operator", (comparison, row, op, value) => {
    expect(COMPARISON_OPERATORS[comparison]).toBe(op);
    expect(compileSentence({ rows: [row], joiner: "and" })).toEqual({
      field: row.path,
      op,
      value,
    });
  });

  it("compiles a row with a ref to a ref leaf", () => {
    const row: SentenceRow = { path: "health", comparison: "at_most", ref: "max_health" };
    expect(compileSentence({ rows: [row], joiner: "and" })).toEqual({
      field: "health",
      op: "<=",
      ref: "max_health",
    });
  });

  it("chains two and three rows with AND", () => {
    expect(compileSentence({ rows: [rowA, rowB], joiner: "and" })).toEqual({
      field: "oil",
      op: "<=",
      value: 2,
      AND: { field: "has_key", op: "==", value: true },
    });
    expect(compileSentence({ rows: [rowA, rowB, rowC], joiner: "and" })).toEqual({
      field: "oil",
      op: "<=",
      value: 2,
      AND: {
        field: "has_key",
        op: "==",
        value: true,
        AND: { field: "time", op: "==", value: "Night" },
      },
    });
  });

  it("chains two and three rows with OR", () => {
    expect(compileSentence({ rows: [rowA, rowB], joiner: "or" })).toEqual({
      field: "oil",
      op: "<=",
      value: 2,
      OR: { field: "has_key", op: "==", value: true },
    });
    const three = compileSentence({ rows: [rowA, rowB, rowC], joiner: "or" });
    expect(three.OR?.OR).toEqual({ field: "time", op: "==", value: "Night" });
  });

  it("refuses an empty sentence", () => {
    expect(() => compileSentence({ rows: [], joiner: "and" })).toThrow();
  });
});

describe("parseExpression", () => {
  const joiners = ["and", "or"] as const;
  const sentences: Sentence[] = ROW_TABLE.flatMap(([, row]) =>
    joiners.map((joiner): Sentence => ({ rows: [row], joiner })),
  ).concat(
    joiners.flatMap((joiner): Sentence[] => [
      { rows: [rowA, rowB], joiner },
      { rows: [rowA, rowB, rowC], joiner },
    ]),
  );

  it.each(sentences)("round-trips with metadata (%j)", (sentence) => {
    const parsed = parseExpression(compileSentence(sentence), buildSentenceMetadata(sentence));
    expect(parsed).toEqual(sentence);
  });

  it("restores drops_to and rises_to from metadata only", () => {
    const sentence: Sentence = {
      rows: [
        { path: "oil", comparison: "drops_to", amount: 2 },
        { path: "trust", comparison: "rises_to", amount: 8 },
      ],
      joiner: "and",
    };
    const expression = compileSentence(sentence);
    expect(parseExpression(expression, buildSentenceMetadata(sentence))).toEqual(sentence);
    const canonical = parseExpression(expression);
    expect(canonical?.rows.map((row) => row.comparison)).toEqual(["at_most", "at_least"]);
  });

  it("ignores metadata that disagrees with the expression", () => {
    const expression = compileSentence({ rows: [rowA], joiner: "and" });
    const parsed = parseExpression(expression, {
      rows: [{ comparison: "rises_to" }],
      joiner: "and",
    });
    expect(parsed?.rows[0].comparison).toBe("at_most");
  });

  it("parses a ref leaf", () => {
    const parsed = parseExpression({ field: "health", op: "<=", ref: "max_health" });
    expect(parsed).toEqual({
      rows: [{ path: "health", comparison: "at_most", ref: "max_health" }],
      joiner: "and",
    });
  });

  it("returns null for mixed and/or chains", () => {
    const mixed: FieldExpression = {
      field: "a",
      op: "==",
      value: true,
      AND: { field: "b", op: "==", value: true, OR: { field: "c", op: "==", value: true } },
    };
    expect(parseExpression(mixed)).toBeNull();
  });

  it.each(["in", "contains", "matches", "!=", "<", ">"] as const)(
    "returns null for the %s operator",
    (op) => {
      expect(parseExpression({ field: "a", op, value: 1 })).toBeNull();
    },
  );

  it("returns null for NOT chains and nested structure", () => {
    const leaf: FieldExpression = { field: "a", op: "==", value: true };
    expect(parseExpression({ ...leaf, NOT: leaf })).toBeNull();
    expect(parseExpression({ NOT: leaf } as unknown as FieldExpression)).toBeNull();
    expect(parseExpression({ field: "a", op: "==", value: 1, AND: undefined })).not.toBeNull();
  });

  it("returns null for a leaf without a value or ref", () => {
    expect(parseExpression({ field: "a", op: "<=" })).toBeNull();
  });
});

describe("while limits", () => {
  const guard: SentenceRow = { path: "in_chapel", comparison: "becomes_yes" };
  const must: SentenceRow = { path: "weapon_drawn", comparison: "becomes_no" };

  it("compiles to the exact chained grammar", () => {
    expect(compileWhileLimit(guard, must)).toEqual({
      field: "weapon_drawn",
      op: "==",
      value: false,
      OR: { NOT: { field: "in_chapel", op: "==", value: true } },
    });
  });

  it("is violated only when the guard is true and the must is false", () => {
    const expression = compileWhileLimit(guard, must) as unknown as Record<string, unknown>;
    const holds = (inChapel: boolean, weaponDrawn: boolean): boolean =>
      evaluate(expression, { in_chapel: inChapel, weapon_drawn: weaponDrawn });
    expect(holds(true, true)).toBe(false);
    expect(holds(true, false)).toBe(true);
    expect(holds(false, true)).toBe(true);
    expect(holds(false, false)).toBe(true);
  });

  it("round-trips through parseWhileLimit", () => {
    expect(parseWhileLimit(compileWhileLimit(guard, must))).toEqual({ guard, must });
  });

  it("rejects shapes that are not a while limit", () => {
    const leaf: FieldExpression = { field: "a", op: "==", value: true };
    expect(parseWhileLimit(leaf)).toBeNull();
    expect(parseWhileLimit({ ...leaf, OR: leaf })).toBeNull();
    expect(parseWhileLimit({ ...leaf, AND: leaf })).toBeNull();
  });
});

describe("semantics against the evaluator", () => {
  const state: State = { oil: 2, has_key: true, time: "Day", health: 3, max_health: 10 };

  it("agrees for and chains", () => {
    const and = compileSentence({ rows: [rowA, rowB], joiner: "and" });
    expect(evaluate(and as unknown as Record<string, unknown>, state)).toBe(true);
    expect(evaluate(and as unknown as Record<string, unknown>, { ...state, has_key: false })).toBe(false);
  });

  it("agrees for or chains", () => {
    const or = compileSentence({ rows: [rowA, rowC], joiner: "or" });
    expect(evaluate(or as unknown as Record<string, unknown>, state)).toBe(true);
    expect(evaluate(or as unknown as Record<string, unknown>, { ...state, oil: 9 })).toBe(false);
  });

  it("agrees for ref leaves", () => {
    const row: SentenceRow = { path: "health", comparison: "at_most", ref: "max_health" };
    const expression = compileSentence({ rows: [row], joiner: "and" });
    expect(evaluate(expression as unknown as Record<string, unknown>, state)).toBe(true);
    expect(evaluate(expression as unknown as Record<string, unknown>, { ...state, health: 12 })).toBe(false);
  });
});

describe("describeSentence", () => {
  const labels = { oil: "Lantern oil", has_key: "Has the key", time: "Time", max_health: "Max health", health: "Health" };

  it("reads as plain words", () => {
    expect(describeSentence({ rows: [rowA, rowB], joiner: "and" }, labels)).toBe(
      "Lantern oil is at most 2 and Has the key is yes",
    );
    expect(describeSentence({ rows: [rowC, rowB], joiner: "or" }, labels)).toBe(
      "Time is Night or Has the key is yes",
    );
  });

  it("keeps the creator's wording for drops and rises", () => {
    const row: SentenceRow = { path: "oil", comparison: "drops_to", amount: 1 };
    expect(describeSentence({ rows: [row], joiner: "and" }, labels)).toBe("Lantern oil drops to 1");
  });

  it("names the other value for a ref row", () => {
    const row: SentenceRow = { path: "health", comparison: "at_most", ref: "max_health" };
    expect(describeSentence({ rows: [row], joiner: "and" }, labels)).toBe("Health is at most Max health");
  });

  it("falls back to the path when a label is missing", () => {
    expect(describeSentence({ rows: [rowA], joiner: "and" }, {})).toBe("oil is at most 2");
  });
});
