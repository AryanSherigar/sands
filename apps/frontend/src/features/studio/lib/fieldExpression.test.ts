import { describe, expect, it } from "vitest";
import { isFieldExpression } from "./fieldExpression";

describe("isFieldExpression", () => {
  it("accepts a leaf and nested connectives", () => {
    expect(isFieldExpression({ field: "trust", op: ">=", value: 8 })).toBe(true);
    expect(
      isFieldExpression({ field: "a", op: "==", value: true, AND: { field: "b", op: "<=", ref: "c" }, NOT: { field: "d", op: "==", value: "x" } }),
    ).toBe(true);
  });

  it.each([
    ["a missing field", { op: "==", value: 1 }],
    ["an unknown operator", { field: "a", op: "~=", value: 1 }],
    ["a bad value type", { field: "a", op: "==", value: [1] }],
    ["a bad nested connective", { field: "a", op: "==", value: 1, AND: { field: 3, op: "==" } }],
    ["a non-object", "trust"],
    ["null", null],
  ])("rejects %s", (_name, value) => {
    expect(isFieldExpression(value)).toBe(false);
  });
});
