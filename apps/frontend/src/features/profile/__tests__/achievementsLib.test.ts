import { describe, expect, it } from "vitest";
import {
  formatEarnedDate,
  formatProgress,
  getProgressWidthClass,
  groupByFamily,
  visibleAchievements,
} from "../lib/achievements";
import { PROGRESS_WIDTH_CLASSES } from "../constants/achievements.constants";
import type { AchievementItem } from "../types/achievements.types";

const item = (
  key: string,
  family: string,
  earned: string | null,
  current = 0,
): AchievementItem => ({
  key,
  name: key,
  family,
  requirement: "r",
  earned_at: earned,
  progress: { current, target: 100 },
});

describe("groupByFamily", () => {
  it("orders families and drops empty ones", () => {
    const groups = groupByFamily([
      item("a", "Creator", null),
      item("b", "Journey", null),
      item("c", "Journey", null),
    ]);
    expect(groups.map((g) => g.family)).toEqual(["Journey", "Creator"]);
    expect(groups[0].items.map((i) => i.key)).toEqual(["b", "c"]);
  });
});

describe("visibleAchievements", () => {
  const all = [
    item("a", "Journey", "2026-10-27T00:00:00Z", 100),
    item("b", "Journey", null, 63),
  ];

  it("keeps everything and progress for the owner", () => {
    expect(visibleAchievements(all, true)).toEqual(all);
  });

  it("shows earned only and strips progress otherwise", () => {
    const visible = visibleAchievements(all, false);
    expect(visible.map((i) => i.key)).toEqual(["a"]);
    expect(visible[0].progress).toBeNull();
  });
});

describe("formatters", () => {
  it("formats progress", () => {
    expect(formatProgress({ current: 63, target: 100 })).toBe("63 / 100");
  });

  it("formats the earned date", () => {
    expect(formatEarnedDate("2026-10-27T00:00:00Z")).toMatch(/^Earned .*2026$/);
  });
});

describe("getProgressWidthClass", () => {
  it("maps ratios to width classes and clamps", () => {
    const widthOf = (current: number, target: number) =>
      getProgressWidthClass({ current, target }, PROGRESS_WIDTH_CLASSES);
    expect(widthOf(0, 100)).toBe("w-0");
    expect(widthOf(50, 100)).toBe("w-[50%]");
    expect(widthOf(100, 100)).toBe("w-full");
    expect(widthOf(500, 100)).toBe("w-full");
    expect(widthOf(3, 0)).toBe("w-0");
  });
});
