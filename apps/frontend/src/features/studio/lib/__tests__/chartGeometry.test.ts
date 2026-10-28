import { describe, expect, it } from "vitest";
import {
  CHART_HEIGHT,
  CHART_LABEL_GUTTER,
  CHART_PADDING,
  CHART_WIDTH,
} from "../../constants/stats";
import { barListWidth, plotBars, plotPoints } from "../chartGeometry";

describe("chartGeometry", () => {
  it("maps the largest value to the top and spreads points across the width", () => {
    const points = plotPoints([
      { label: "a", value: 0 },
      { label: "b", value: 10 },
    ]);
    expect(points[0]?.x).toBe(CHART_PADDING);
    expect(points[1]?.x).toBe(CHART_WIDTH - CHART_PADDING);
    expect(points[1]?.y).toBe(CHART_PADDING);
    expect(points[0]?.y).toBe(CHART_HEIGHT - CHART_PADDING);
  });

  it("gives bars heights proportional to value above the label gutter", () => {
    const [half, full] = plotBars([
      { label: "a", value: 5 },
      { label: "b", value: 10 },
    ]);
    const baseline = CHART_HEIGHT - CHART_LABEL_GUTTER;
    expect((full?.y ?? 0) + (full?.height ?? 0)).toBe(baseline);
    expect(half?.height).toBe((full?.height ?? 0) / 2);
  });

  it("clamps bar list widths", () => {
    expect(barListWidth(-1)).toBe(0);
    expect(barListWidth(2)).toBe(barListWidth(1));
  });
});
