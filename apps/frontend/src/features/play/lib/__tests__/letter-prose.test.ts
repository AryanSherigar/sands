import { describe, expect, it } from "vitest";
import { joinProse, splitProse } from "../letter-prose";

describe("splitProse", () => {
  it("splits on blank lines and trims each paragraph", () => {
    expect(splitProse("First thought.\n\n  Second thought. \n\n\nThird.")).toEqual([
      "First thought.",
      "Second thought.",
      "Third.",
    ]);
  });

  it("keeps a single paragraph whole, including single line breaks", () => {
    expect(splitProse("One line\nstill one paragraph")).toEqual([
      "One line\nstill one paragraph",
    ]);
  });

  it("returns one empty paragraph for blank prose so the quill has a line to edit", () => {
    expect(splitProse("  \n\n ")).toEqual([""]);
  });
});

describe("joinProse", () => {
  it("joins paragraphs with a blank line and drops empty ones", () => {
    expect(joinProse(["A.", "", "B."])).toBe("A.\n\nB.");
  });

  it("round-trips split prose", () => {
    const prose = "Alpha.\n\nBeta.";
    expect(joinProse(splitProse(prose))).toBe(prose);
  });
});
