import { describe, expect, it } from "vitest";
import { STYLE_CHIPS } from "../constants/styleChips";
import { isStyleChipOn, toggleStyleChip } from "./styleChips";

const [novel, punchy] = STYLE_CHIPS;

describe("style chips", () => {
  it("has ready-made wording for each of the seven chips", () => {
    expect(STYLE_CHIPS.map((chip) => chip.label)).toEqual([
      "Like a novel",
      "Short & punchy",
      "Dark & gritty",
      "Cozy",
      "Funny",
      "Like a game master",
      "Poetic",
    ]);
    STYLE_CHIPS.forEach((chip) => expect(chip.wording.length).toBeGreaterThan(20));
  });

  it("adds an editable linked block carrying the chip's wording", () => {
    const next = toggleStyleChip({ blocks: [] }, novel);

    expect(next.blocks).toEqual([
      {
        kind: "answer",
        question_id: "style-chip-like-a-novel",
        label: "Like a novel",
        text: novel.wording,
      },
    ]);
    expect(isStyleChipOn(next, novel)).toBe(true);
  });

  it("removes the block when the chip is toggled off and keeps other blocks", () => {
    const withBoth = toggleStyleChip(toggleStyleChip({ blocks: [] }, novel), punchy);
    const withoutNovel = toggleStyleChip(withBoth, novel);

    expect(isStyleChipOn(withoutNovel, novel)).toBe(false);
    expect(isStyleChipOn(withoutNovel, punchy)).toBe(true);
  });
});
