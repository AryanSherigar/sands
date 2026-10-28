import { describe, expect, it } from "vitest";
import { findWords, selectDistortedWords } from "./selectDistortedWords";

const LONG_TEXT = Array.from({ length: 4000 }, (_, i) => `word${i}`).join(" ");

describe("selectDistortedWords", () => {
  it("is deterministic for the same inputs", () => {
    const first = selectDistortedWords(LONG_TEXT, "pt-1", 3);
    expect([...selectDistortedWords(LONG_TEXT, "pt-1", 3)]).toEqual([...first]);
  });

  it("picks about 5% of the words", () => {
    const ratio = selectDistortedWords(LONG_TEXT, "pt-1", 3).size / 4000;
    expect(ratio).toBeGreaterThan(0.04);
    expect(ratio).toBeLessThan(0.06);
  });

  it("draws differently per turn and per paragraph", () => {
    const base = [...selectDistortedWords(LONG_TEXT, "pt-1", 3)];
    expect([...selectDistortedWords(LONG_TEXT, "pt-1", 4)]).not.toEqual(base);
    expect(
      [...selectDistortedWords(LONG_TEXT, "pt-1", 3, { paragraphIndex: 1 })],
    ).not.toEqual(base);
  });

  it("never picks words of two letters or fewer", () => {
    const text = Array.from({ length: 4000 }, () => "to of it").join(" ");
    expect(selectDistortedWords(text, "pt-1", 1).size).toBe(0);
  });

  it("never picks a word that overlaps a protected range", () => {
    const everything = selectDistortedWords(LONG_TEXT, "pt-1", 3);
    const first = findWords(LONG_TEXT)[[...everything][0]];
    const picked = selectDistortedWords(LONG_TEXT, "pt-1", 3, {
      protectedRanges: [[first.start + 1, first.start + 2]],
    });
    expect(picked.has(first.index)).toBe(false);
    expect(picked.size).toBe(everything.size - 1);
  });

  it("is prefix-stable while the text streams in", () => {
    const words = LONG_TEXT.split(" ");
    const finalSelection = selectDistortedWords(LONG_TEXT, "pt-1", 3);
    for (const prefixLength of [10, 200, 1500]) {
      const prefix = `${words.slice(0, prefixLength).join(" ")} `;
      for (const index of selectDistortedWords(prefix, "pt-1", 3, {
        isComplete: false,
      })) {
        expect(finalSelection.has(index)).toBe(true);
      }
    }
  });

  it("holds back a trailing word that may still be arriving", () => {
    const words = LONG_TEXT.split(" ").slice(0, 600);
    const text = words.join(" ");
    const lastIndex = words.length - 1;
    const streaming = selectDistortedWords(text, "pt-1", 3, { isComplete: false });

    expect(streaming.has(lastIndex)).toBe(false);
  });
});

describe("findWords", () => {
  it("returns offsets and sequential indices", () => {
    expect(findWords("a  bc d")).toEqual([
      { index: 0, start: 0, end: 1 },
      { index: 1, start: 3, end: 5 },
      { index: 2, start: 6, end: 7 },
    ]);
  });
});
