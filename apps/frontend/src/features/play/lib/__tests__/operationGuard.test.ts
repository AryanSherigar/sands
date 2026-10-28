import { describe, it, expect } from "vitest";
import { buildOperationGuard } from "../operationGuard";

describe("buildOperationGuard", () => {
  const world = { world_version: 7, turn: 3, wave: 1 };

  it("copies the expected version, turn and wave from the world", () => {
    expect(buildOperationGuard(world, "op-1")).toEqual({
      operation_id: "op-1",
      expected_world_version: 7,
      expected_turn: 3,
      expected_wave: 1,
    });
  });

  it("generates a distinct operation id per call", () => {
    expect(buildOperationGuard(world).operation_id).not.toBe(
      buildOperationGuard(world).operation_id,
    );
  });
});
