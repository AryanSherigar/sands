import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { buildEntityFixture, buildFactFixture } from "../test/cardApiMock";
import { createGuideWrapper } from "../test/guideHookWrapper";
import {
  buildConditionFixture,
  buildEndConditionFixture,
  buildInvariantFixture,
  buildScenarioFixture,
  installStudioApi,
} from "../test/studioApiMock";
import { useUsedIn } from "./useUsedIn";

describe("useUsedIn", () => {
  it("finds a value inside nested AND, OR, NOT and ref expressions, and in link conditions", async () => {
    installStudioApi({
      scenario: buildScenarioFixture({ mode: "master" }),
      entities: [
        buildEntityFixture({ entity_id: "a", canonical_name: "Ada" }),
        buildEntityFixture({ entity_id: "b", canonical_name: "Bo" }),
      ],
      facts: [
        buildFactFixture({
          fact_id: "f1",
          subject_entity_id: "a",
          predicate: "trusts",
          object_entity_id: "b",
          when_active: { field: "oil", op: ">=", value: 1 },
        }),
      ],
      endConditions: [
        buildEndConditionFixture({
          end_condition_id: "e1",
          condition_expression: { field: "a", op: "==", value: 1, AND: { field: "oil", op: "<=", value: 0 } },
        }),
      ],
      conditions: [
        buildConditionFixture({
          condition_id: "c1",
          condition_expression: { field: "a", op: "==", value: 1, OR: { NOT: { field: "oil", op: "==", value: 3 } } },
        }),
      ],
      invariants: [
        buildInvariantFixture({
          invariant_id: "i1",
          invariant_expression: { field: "health", op: "<=", ref: "oil" },
        }),
        buildInvariantFixture({ invariant_id: "i2", invariant_expression: { field: "other", op: "==", value: 1 } }),
      ],
    });
    const { Wrapper } = createGuideWrapper();
    const { result } = renderHook(() => useUsedIn("oil"), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.total).toBe(4));
    expect(result.current.endings.map((row) => row.end_condition_id)).toEqual(["e1"]);
    expect(result.current.rules.map((row) => row.condition_id)).toEqual(["c1"]);
    expect(result.current.limits.map((row) => row.invariant_id)).toEqual(["i1"]);
    expect(result.current.links.map((row) => row.fact_id)).toEqual(["f1"]);
  });
});
