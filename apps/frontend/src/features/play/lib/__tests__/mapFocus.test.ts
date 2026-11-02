import { describe, expect, it } from "vitest";
import { MAP_FOCUS_SCALE, computeFocusTransform, findRegionLabelPoint } from "../mapFocus";

describe("mapFocus", () => {
  it("centres the point in the viewport at the focus scale", () => {
    const transform = computeFocusTransform({ x: 400, y: 200 }, { width: 1000, height: 600 });

    expect(transform).toEqual({
      positionX: 500 - 400 * MAP_FOCUS_SCALE,
      positionY: 300 - 200 * MAP_FOCUS_SCALE,
      scale: MAP_FOCUS_SCALE,
    });
  });

  it("returns null for an unknown region", () => {
    expect(findRegionLabelPoint([], "missing")).toBeNull();
  });
});
