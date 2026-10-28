import { describe, expect, it } from "vitest";
import { buildLabelMap } from "./buildLabelMap";
import { addNoise, makeBlockImage } from "./testImages";
import type { PixelImage } from "@/shared/types/strategy-map.types";

const PALETTE: Record<string, [number, number, number]> = {
  r: [255, 0, 0],
  g: [0, 160, 40],
  b: [0, 60, 250],
  y: [250, 250, 0],
};
const CELL = 30;

function paintRect(
  image: PixelImage,
  rect: { x: number; y: number; size: number },
  rgb: [number, number, number],
): void {
  for (let y = rect.y; y < rect.y + rect.size; y++) {
    for (let x = rect.x; x < rect.x + rect.size; x++) {
      image.data.set(rgb, (y * image.width + x) * 4);
    }
  }
}

function paintBox(
  image: PixelImage,
  box: { x: number; y: number; width: number; height: number },
  rgb: [number, number, number],
): void {
  for (let y = box.y; y < box.y + box.height; y++) {
    for (let x = box.x; x < box.x + box.width; x++) {
      image.data.set(rgb, (y * image.width + x) * 4);
    }
  }
}

describe("buildLabelMap", () => {
  it("finds the real regions in a noisy flat-colour image", () => {
    const flat = makeBlockImage(["rrg", "rrg", "bbb"], PALETTE, CELL);
    const { labelMap, warnings } = buildLabelMap(addNoise(flat, 6, 1));
    expect(labelMap.entries).toHaveLength(3);
    expect(warnings.filter((w) => w.kind === "folded_color")).toHaveLength(0);
  });

  it("folds a stray colour and reports it once", () => {
    const image = makeBlockImage(["rrg", "rrg", "bbb"], PALETTE, CELL);
    paintRect(image, { x: 4, y: 4, size: 4 }, PALETTE.y);
    const { labelMap, warnings } = buildLabelMap(image);
    expect(labelMap.entries).toHaveLength(3);
    expect(warnings.filter((w) => w.kind === "folded_color")).toHaveLength(1);
  });

  it("carries the folded colour so it can be promoted to a seed", () => {
    const image = makeBlockImage(["rrg", "rrg", "bbb"], PALETTE, CELL);
    paintRect(image, { x: 4, y: 4, size: 4 }, PALETTE.y);
    const { warnings } = buildLabelMap(image);
    expect(warnings.find((w) => w.kind === "folded_color")?.rgb).toEqual(PALETTE.y);
  });

  it("keeps one region for a colour split into two pieces", () => {
    const image = makeBlockImage(["rgr", "rgr", "rgr"], PALETTE, CELL);
    const { labelMap } = buildLabelMap(image);
    expect(labelMap.entries).toHaveLength(2);
  });

  it("allocates ids by pixel count, largest first", () => {
    const image = makeBlockImage(["rrg", "rrg", "rrg"], PALETTE, CELL);
    const { labelMap } = buildLabelMap(image);
    expect(labelMap.entries.map((entry) => entry.id)).toEqual([
      "region_01",
      "region_02",
    ]);
    expect(labelMap.entries[0].sourceColor).toBe("#ff0000");
    expect(labelMap.nextIdNumber).toBe(3);
  });

  it("is deterministic", () => {
    const image = addNoise(makeBlockImage(["rg", "bg"], PALETTE, CELL), 5, 3);
    const first = buildLabelMap(image).labelMap;
    const second = buildLabelMap(image).labelMap;
    expect(Array.from(first.labels)).toEqual(Array.from(second.labels));
  });

  it("keeps a folded colour as its own region when forced as a seed", () => {
    const image = makeBlockImage(["rrg", "rrg", "bbb"], PALETTE, CELL);
    paintRect(image, { x: 4, y: 4, size: 4 }, PALETTE.y);
    const { labelMap } = buildLabelMap(image, [PALETTE.y]);
    expect(labelMap.entries).toHaveLength(4);
  });

  it("rejects pixel data of the wrong length", () => {
    const bad = { width: 2, height: 2, data: new Uint8ClampedArray(4) };
    expect(() => buildLabelMap(bad)).toThrow(Error);
  });

  it("merges a thin edge-blur stripe into its neighbours and reports it", () => {
    const image = makeBlockImage(["rb", "rb"], PALETTE, 50);
    paintBox(image, { x: 48, y: 0, width: 3, height: 100 }, PALETTE.g);
    const { labelMap, warnings } = buildLabelMap(image);
    expect(labelMap.entries).toHaveLength(2);
    const folded = warnings.find((w) => w.kind === "folded_color");
    expect(folded?.rgb).toEqual(PALETTE.g);
  });

  it("keeps a small region that is thick enough to be real", () => {
    const image = makeBlockImage(["rr", "rr"], PALETTE, 50);
    paintBox(image, { x: 30, y: 30, width: 30, height: 30 }, PALETTE.y);
    const { labelMap } = buildLabelMap(image);
    expect(labelMap.entries).toHaveLength(2);
  });
});
