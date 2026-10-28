import { describe, expect, it } from "vitest";
import {
  addRegion,
  createEmptyLabelMap,
  deleteRegion,
  downscaleLabelMap,
  mergeRegions,
  paintBrush,
  paintMask,
  splitRegion,
} from "./editOps";
import { makeLabelMapFromRows } from "./testImages";
import type { LabelMap } from "@/shared/types/strategy-map.types";

function snapshot(map: LabelMap): string {
  return JSON.stringify({ ...map, labels: Array.from(map.labels) });
}

function pixelsOf(map: LabelMap, id: string): number {
  const label = map.entries.find((entry) => entry.id === id)?.label ?? -1;
  return map.labels.filter((value) => value === label).length;
}

describe("mergeRegions", () => {
  it("moves the removed region's pixels to the kept one", () => {
    const map = makeLabelMapFromRows(["aab", "aab"]);
    const before = snapshot(map);
    const merged = mergeRegions(map, "region_01", "region_02");
    expect(merged.entries.map((entry) => entry.id)).toEqual(["region_01"]);
    expect(pixelsOf(merged, "region_01")).toBe(6);
    expect(snapshot(map)).toBe(before);
  });
});

describe("deleteRegion", () => {
  it("unassigns the pixels and drops the entry", () => {
    const map = makeLabelMapFromRows(["ab"]);
    const result = deleteRegion(map, "region_02");
    expect(Array.from(result.labels)).toEqual([1, 0]);
    expect(result.entries).toHaveLength(1);
  });
});

describe("addRegion", () => {
  it("never reuses an id after a delete", () => {
    const map = makeLabelMapFromRows(["ab.", "ab."]);
    const withoutB = deleteRegion(map, "region_02");
    const mask = new Uint8Array(6);
    mask[2] = 1;
    mask[5] = 1;
    const { map: added, id } = addRegion(withoutB, mask, "#00ff00");
    expect(id).toBe("region_03");
    expect(added.entries.find((entry) => entry.id === id)?.sourceColor).toBe("#00ff00");
    expect(pixelsOf(added, id)).toBe(2);
  });
});

describe("paintMask and paintBrush", () => {
  it("paints only masked pixels", () => {
    const map = makeLabelMapFromRows(["aab"]);
    const result = paintMask(map, new Uint8Array([0, 1, 0]), "region_02");
    expect(Array.from(result.labels)).toEqual([1, 2, 2]);
  });

  it("paints a single pixel at radius 0 and clips at the border", () => {
    const map = makeLabelMapFromRows(["aaa", "aab", "aaa"]);
    const dot = paintBrush(map, { x: 0, y: 0 }, 0, "region_02");
    expect(dot.labels[0]).toBe(2);
    expect(pixelsOf(dot, "region_02")).toBe(2);
    expect(() => paintBrush(map, { x: 0, y: 0 }, 2, "region_02")).not.toThrow();
  });

  it("drops a region painted over completely", () => {
    const map = makeLabelMapFromRows(["ab"]);
    const result = paintMask(map, new Uint8Array([0, 1]), "region_01");
    expect(result.entries.map((entry) => entry.id)).toEqual(["region_01"]);
  });
});

describe("splitRegion", () => {
  it("keeps the id on the larger piece and gives the other a new id", () => {
    const map = makeLabelMapFromRows(["aaaaaaaa", "aaaaaaaa"]);
    const before = snapshot(map);
    const result = splitRegion(map, "region_01", [
      { x: 3, y: 0 },
      { x: 3, y: 1 },
    ]);
    expect(result.entries.map((entry) => entry.id)).toEqual(["region_01", "region_02"]);
    expect(result.labels[7]).toBe(1);
    expect(result.labels[0]).toBe(2);
    expect(result.labels.every((label) => label !== 0)).toBe(true);
    expect(snapshot(map)).toBe(before);
  });

  it("returns an equal map when the cut does not separate anything", () => {
    const map = makeLabelMapFromRows(["aaaa", "aaaa"]);
    const result = splitRegion(map, "region_01", [
      { x: 1, y: 0 },
      { x: 1, y: 0 },
    ]);
    expect(result.entries).toHaveLength(1);
  });
});

describe("downscaleLabelMap", () => {
  it("samples every nth pixel", () => {
    const map = makeLabelMapFromRows(["abab", "abab", "cdcd", "cdcd"]);
    const small = downscaleLabelMap(map, 2);
    expect(small.width).toBe(2);
    expect(Array.from(small.labels)).toEqual([1, 1, 3, 3]);
  });
});

describe("createEmptyLabelMap", () => {
  it("starts with every pixel unassigned and the first id free", () => {
    const map = createEmptyLabelMap(3, 2);
    expect(map.labels).toHaveLength(6);
    expect(map.labels.every((label) => label === 0)).toBe(true);
    const mask = new Uint8Array(6);
    mask[0] = 1;
    expect(addRegion(map, mask, null).id).toBe("region_01");
  });
});
