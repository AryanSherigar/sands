import { describe, expect, it } from "vitest";
import { extractArcs } from "./extractArcs";
import { makeLabelMapFromRows } from "./testImages";
import type { Arc } from "@/shared/types/strategy-map.types";

function arcBetween(arcs: Arc[], first: number, second: number): Arc[] {
  return arcs.filter(
    (arc) =>
      (arc.left === first && arc.right === second) ||
      (arc.left === second && arc.right === first),
  );
}

function edgeCount(arc: Arc): number {
  return arc.isClosed ? arc.points.length : arc.points.length - 1;
}

function countBoundaryEdges(rows: string[]): number {
  const height = rows.length;
  const width = rows[0].length;
  const at = (x: number, y: number): string =>
    x < 0 || y < 0 || x >= width || y >= height ? "." : rows[y][x];
  let total = 0;
  for (let y = 0; y <= height; y++) {
    for (let x = 0; x <= width; x++) {
      if (at(x - 1, y) !== at(x, y) && y < height) total++;
      if (at(x, y - 1) !== at(x, y) && x < width) total++;
    }
  }
  return total;
}

describe("extractArcs", () => {
  it("gives two side-by-side blocks one interior arc as long as the block", () => {
    const arcs = extractArcs(makeLabelMapFromRows(["aabb", "aabb", "aabb"]));
    const interior = arcBetween(arcs, 1, 2);
    expect(interior).toHaveLength(1);
    expect(interior[0].points).toHaveLength(4);
    expect(interior[0].points.every((point) => point.x === 2)).toBe(true);
  });

  it("closes the arc around an enclave", () => {
    const rows = ["aaaaa", "aabaa", "aaaaa"];
    const interior = arcBetween(extractArcs(makeLabelMapFromRows(rows)), 1, 2);
    expect(interior).toHaveLength(1);
    expect(interior[0].isClosed).toBe(true);
    expect(interior[0].points).toHaveLength(4);
  });

  it("splits at a four-way corner into four interior arcs", () => {
    const rows = ["ab", "cd"];
    const arcs = extractArcs(makeLabelMapFromRows(rows));
    const interior = arcs.filter((arc) => arc.left !== 0 && arc.right !== 0);
    expect(interior).toHaveLength(4);
    expect(interior.every((arc) => edgeCount(arc) === 1)).toBe(true);
  });

  it("covers every boundary edge exactly once", () => {
    const rows = ["aab.", "abbc", ".bcc"];
    const arcs = extractArcs(makeLabelMapFromRows(rows));
    const covered = arcs.reduce((sum, arc) => sum + edgeCount(arc), 0);
    expect(covered).toBe(countBoundaryEdges(rows));
  });

  it("is deterministic", () => {
    const map = makeLabelMapFromRows(["aab", "abb"]);
    expect(JSON.stringify(extractArcs(map))).toBe(
      JSON.stringify(extractArcs(map)),
    );
  });
});
