import { describe, expect, it } from "vitest";
import { smoothLabels } from "./smoothLabels";
import { makeLabelMapFromRows } from "./testImages";

function rowsAfterSmoothing(rows: string[]): number[][] {
  const map = makeLabelMapFromRows(rows);
  const smoothed = smoothLabels(map.labels, map.width, map.height);
  return rows.map((_, y) => Array.from(smoothed.slice(y * map.width, (y + 1) * map.width)));
}

describe("smoothLabels", () => {
  it("removes a one-pixel stripe of a foreign label between two regions", () => {
    const rows = ["aaaaabbbbb", "aaaaabbbbb", "aaaaabbbbb", "aaaaabbbbb", "aaaaabbbbb"].map(
      (row) => row.slice(0, 5) + "c" + row.slice(5, 9),
    );
    const result = rowsAfterSmoothing(rows);
    expect(result.every((row) => !row.includes(2))).toBe(true);
  });

  it("keeps a thick block untouched", () => {
    const rows = Array(8).fill("aaaabbbb");
    const map = makeLabelMapFromRows(rows);
    expect(Array.from(smoothLabels(map.labels, map.width, map.height))).toEqual(Array.from(map.labels));
  });

  it("does not change its input", () => {
    const map = makeLabelMapFromRows(["abab", "abab"]);
    const before = Array.from(map.labels);
    smoothLabels(map.labels, map.width, map.height);
    expect(Array.from(map.labels)).toEqual(before);
  });

  it("leaves unassigned pixels unassigned", () => {
    const map = makeLabelMapFromRows(["a.a", "a.a", "a.a"]);
    const result = smoothLabels(map.labels, map.width, map.height);
    expect(result[1]).toBe(0);
  });
});
