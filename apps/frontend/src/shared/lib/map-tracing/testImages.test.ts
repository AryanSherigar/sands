import { describe, expect, it } from "vitest";
import { addNoise, makeBlockImage, makeLabelMapFromRows } from "./testImages";

const PALETTE: Record<string, [number, number, number]> = {
  a: [255, 0, 0],
  b: [0, 255, 0],
};

function pixelAt(
  image: { width: number; data: Uint8ClampedArray },
  x: number,
  y: number,
): number[] {
  const offset = (y * image.width + x) * 4;
  return Array.from(image.data.slice(offset, offset + 3));
}

describe("makeBlockImage", () => {
  it("expands each character into a flat cell", () => {
    const image = makeBlockImage(["ab", "ba"], PALETTE, 2);
    expect(image.width).toBe(4);
    expect(image.height).toBe(4);
    expect(pixelAt(image, 0, 0)).toEqual([255, 0, 0]);
    expect(pixelAt(image, 2, 0)).toEqual([0, 255, 0]);
  });
});

describe("addNoise", () => {
  it("is deterministic for the same seed", () => {
    const base = makeBlockImage(["ab"], PALETTE, 3);
    const first = addNoise(base, 6, 1);
    const second = addNoise(base, 6, 1);
    expect(Array.from(first.data)).toEqual(Array.from(second.data));
  });

  it("changes each channel by at most the amplitude", () => {
    const base = makeBlockImage(["ab"], PALETTE, 3);
    const noisy = addNoise(base, 6, 1);
    const isWithinAmplitude = Array.from(noisy.data).every(
      (value, index) => Math.abs(value - base.data[index]) <= 6,
    );
    expect(isWithinAmplitude).toBe(true);
    expect(Array.from(noisy.data)).not.toEqual(Array.from(base.data));
  });
});

describe("makeLabelMapFromRows", () => {
  it("maps characters to labels by first appearance and dots to 0", () => {
    const map = makeLabelMapFromRows(["ab.", "bba"]);
    expect(map.width).toBe(3);
    expect(map.height).toBe(2);
    expect(Array.from(map.labels)).toEqual([1, 2, 0, 2, 2, 1]);
    expect(map.entries.map((entry) => entry.id)).toEqual([
      "region_01",
      "region_02",
    ]);
    expect(map.nextIdNumber).toBe(3);
  });
});
