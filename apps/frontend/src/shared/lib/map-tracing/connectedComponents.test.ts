import { describe, expect, it } from "vitest";
import { connectedComponents } from "./connectedComponents";

describe("connectedComponents", () => {
  it("separates same-label pieces that do not touch", () => {
    // 1 0 1
    const labels = new Uint16Array([1, 2, 1]);
    const result = connectedComponents(labels, 3, 1);
    expect(result.sizes).toEqual([1, 1, 1]);
    expect(result.labelOf).toEqual([1, 2, 1]);
  });

  it("joins pieces through 4-neighbour contact only", () => {
    // 1 2
    // 2 1  — every pair touches only diagonally
    const labels = new Uint16Array([1, 2, 2, 1]);
    const result = connectedComponents(labels, 2, 2);
    expect(result.sizes).toEqual([1, 1, 1, 1]);
  });

  it("gives unassigned pixels component id -1", () => {
    const labels = new Uint16Array([0, 1]);
    const result = connectedComponents(labels, 2, 1);
    expect(result.ids[0]).toBe(-1);
    expect(result.ids[1]).toBe(0);
  });
});
