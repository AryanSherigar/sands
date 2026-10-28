import { describe, expect, it } from "vitest";
import { assembleOutline, computeLabelPoint } from "./assembleRegions";
import { extractArcs } from "./extractArcs";
import { makeLabelMapFromRows } from "./testImages";

function outlineOf(rows: string[], label: number): string {
  const map = makeLabelMapFromRows(rows);
  return assembleOutline(label, extractArcs(map));
}

function subpathCount(outline: string): number {
  return outline.split("M").length - 1;
}

describe("assembleOutline", () => {
  it("draws a square as four corners starting top-left", () => {
    const rows = ["aaaa", "aaaa", "aaaa", "aaaa"];
    expect(outlineOf(rows, 1)).toBe("M0 0 L4 0 L4 4 L0 4 Z");
  });

  it("gives a region with an enclave an extra subpath, and the enclave one", () => {
    const rows = ["aaaaa", "aabaa", "aaaaa"];
    expect(subpathCount(outlineOf(rows, 1))).toBe(2);
    expect(outlineOf(rows, 2)).toBe("M2 1 L3 1 L3 2 L2 2 Z");
  });

  it("gives a region in two separate pieces two subpaths", () => {
    const rows = ["aba", "aba"];
    expect(subpathCount(outlineOf(rows, 1))).toBe(2);
  });

  it("orders subpaths by their top-left vertex", () => {
    const rows = ["aba", "aba"];
    const outline = outlineOf(rows, 1);
    expect(outline.startsWith("M0 0")).toBe(true);
    expect(outline.indexOf("M2 0")).toBeGreaterThan(0);
  });
});

describe("computeLabelPoint", () => {
  it("lies inside a C-shaped region", () => {
    const rows = ["aaaaa", "aa...", "aa...", "aaaaa"];
    const map = makeLabelMapFromRows(rows);
    const point = computeLabelPoint(map, 1);
    expect(map.labels[point.y * map.width + point.x]).toBe(1);
  });

  it("prefers the thickest part of the region", () => {
    const rows = ["aaaaaaa", "aaaaaaa", "aaaaaaa", "..aaa..", "..aaa.."];
    const map = makeLabelMapFromRows(rows);
    expect(computeLabelPoint(map, 1)).toEqual({ x: 3, y: 2 });
  });
});
