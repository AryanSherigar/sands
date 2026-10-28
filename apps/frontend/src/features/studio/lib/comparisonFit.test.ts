import { describe, expect, it } from "vitest";
import type { FieldExpression } from "../components/ConditionEditor/ExpressionBuilder/ExpressionBuilder.types";
import type { ValueOption } from "../types/sentence.types";
import { buildEndConditionFixture } from "../test/studioApiMock";
import { countMisfitPlaces, findMisfitLabels } from "./comparisonFit";

const TRUST: ValueOption = { path: "trust", label: "Trust", kind: "boolean", source: "tracked" };

describe("findMisfitLabels", () => {
  it("flags a number comparison on a value that became yes / no", () => {
    const expression: FieldExpression = { field: "trust", op: ">=", value: 8 };
    expect(findMisfitLabels(expression, undefined, [TRUST])).toEqual(["Trust"]);
  });

  it("accepts a comparison that still fits and ignores missing values", () => {
    const expression: FieldExpression = { field: "trust", op: "==", value: true };
    expect(findMisfitLabels(expression, undefined, [TRUST])).toEqual([]);
    expect(findMisfitLabels({ field: "gone", op: ">=", value: 1 }, undefined, [TRUST])).toEqual([]);
    expect(findMisfitLabels(null, undefined, [TRUST])).toEqual([]);
  });
});

describe("countMisfitPlaces", () => {
  it("counts only the places whose comparison no longer fits the value", () => {
    const misfit = buildEndConditionFixture({
      end_condition_id: "a",
      condition_expression: { field: "trust", op: ">=", value: 8 },
    });
    const fits = buildEndConditionFixture({
      end_condition_id: "b",
      condition_expression: { field: "trust", op: "==", value: true },
    });
    expect(countMisfitPlaces(TRUST, { endings: [misfit, fits], rules: [], limits: [] })).toBe(1);
  });
});
