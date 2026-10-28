import { describe, expect, it } from "vitest";
import { moveItem } from "./moveItem";

describe("moveItem", () => {
  it("moves an item down and up", () => {
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a", "b", "c"], 2, 1)).toEqual(["a", "c", "b"]);
  });

  it("returns a copy unchanged when an index is out of range", () => {
    const items = ["a", "b"];
    const result = moveItem(items, 0, -1);
    expect(result).toEqual(["a", "b"]);
    expect(result).not.toBe(items);
    expect(moveItem(items, 5, 0)).toEqual(["a", "b"]);
  });
});
