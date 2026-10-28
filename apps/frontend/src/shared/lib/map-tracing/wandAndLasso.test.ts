import { describe, expect, it } from "vitest";
import { edgeStrength, floodSelect, polygonMask, snapToEdge } from "./wandAndLasso";
import { makeBlockImage } from "./testImages";

const PALETTE: Record<string, [number, number, number]> = {
  w: [255, 255, 255],
  k: [0, 0, 0],
};

describe("floodSelect", () => {
  it("stops at a line of a different colour", () => {
    const picture = makeBlockImage(["wwwkwww", "wwwkwww", "wwwkwww"], PALETTE, 1);
    const mask = floodSelect(picture, { x: 0, y: 1 }, 10);
    expect(mask.reduce((sum, value) => sum + value, 0)).toBe(9);
    expect(mask[3]).toBe(0);
  });

  it("selects across small colour differences within tolerance", () => {
    const picture = makeBlockImage(["wwww"], PALETTE, 1);
    picture.data[4] = 250;
    expect(floodSelect(picture, { x: 0, y: 0 }, 10).every((value) => value === 1)).toBe(true);
  });
});

describe("edgeStrength and snapToEdge", () => {
  const picture = makeBlockImage(Array(9).fill("wwwwkwwww"), PALETTE, 1);
  const strength = edgeStrength(picture);

  it("moves a point onto a nearby edge", () => {
    const snapped = snapToEdge(strength, picture.width, { x: 1, y: 4 }, 4);
    expect(strength[snapped.y * picture.width + snapped.x]).toBeGreaterThan(0);
    expect(Math.abs(snapped.x - 1)).toBeLessThanOrEqual(4);
  });

  it("leaves the point alone when there is no edge in reach", () => {
    expect(snapToEdge(strength, picture.width, { x: 0, y: 4 }, 1)).toEqual({ x: 0, y: 4 });
  });
});

describe("polygonMask", () => {
  it("fills the pixels whose centres are inside a triangle", () => {
    const mask = polygonMask(8, 8, [
      { x: 0, y: 0 },
      { x: 8, y: 0 },
      { x: 0, y: 8 },
    ]);
    expect(mask.reduce((sum, value) => sum + value, 0)).toBe(28);
  });
});
