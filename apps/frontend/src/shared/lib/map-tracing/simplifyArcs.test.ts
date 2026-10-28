import { describe, expect, it } from "vitest";
import { simplifyArcs, simplifyPolyline } from "./simplifyArcs";
import type { Arc, Point } from "@/shared/types/strategy-map.types";

function staircase(steps: number): Point[] {
  const points: Point[] = [{ x: 0, y: 0 }];
  for (let i = 0; i < steps; i++) {
    points.push({ x: i + 1, y: i }, { x: i + 1, y: i + 1 });
  }
  return points;
}

describe("simplifyPolyline", () => {
  it("drops staircase points within tolerance but keeps the endpoints", () => {
    const input = staircase(10);
    const output = simplifyPolyline(input, 1.5, false);
    expect(output.length).toBeLessThan(input.length);
    expect(output[0]).toEqual(input[0]);
    expect(output[output.length - 1]).toEqual(input[input.length - 1]);
  });

  it("returns the input when tolerance is zero", () => {
    const input = staircase(4);
    expect(simplifyPolyline(input, 0, false)).toEqual(input);
  });

  it("keeps a closed ring closed with at least three points", () => {
    const ring: Point[] = [
      { x: 0, y: 0 },
      { x: 5, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
      { x: 0, y: 10 },
    ];
    const output = simplifyPolyline(ring, 1.5, true);
    expect(output).toEqual([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
      { x: 0, y: 10 },
    ]);
  });
});

describe("simplifyArcs", () => {
  const arc: Arc = {
    id: 7,
    left: 1,
    right: 2,
    points: staircase(10),
    isClosed: false,
  };

  it("simplifies each arc with its own tolerance, once", () => {
    const [result] = simplifyArcs([arc], new Map([[7, 1.5]]));
    expect(result.points).toEqual(simplifyPolyline(arc.points, 1.5, false));
    expect(result.left).toBe(1);
    expect(result.right).toBe(2);
  });

  it("leaves arcs without a tolerance untouched", () => {
    const [result] = simplifyArcs([arc], new Map());
    expect(result.points).toEqual(arc.points);
  });

  it("keeps integer coordinates", () => {
    const [result] = simplifyArcs([arc], new Map([[7, 2]]));
    expect(result.points.every((p) => Number.isInteger(p.x) && Number.isInteger(p.y))).toBe(true);
  });
});
