import { describe, expect, it } from "vitest";
import { addCustomMood, toggleTag } from "./guideTags";

describe("guideTags", () => {
  it("toggles a tag and keeps pick order so the first stays primary", () => {
    expect(toggleTag(["Mystery"], "Horror")).toEqual(["Mystery", "Horror"]);
    expect(toggleTag(["Mystery", "Horror"], "Mystery")).toEqual(["Horror"]);
  });

  it("adds a custom mood once, trimmed and lower-cased", () => {
    expect(addCustomMood(["eerie"], "  Salty ")).toEqual(["eerie", "salty"]);
    expect(addCustomMood(["eerie"], "EERIE")).toEqual(["eerie"]);
    expect(addCustomMood(["eerie"], "   ")).toEqual(["eerie"]);
  });

  it("stops at 12 moods", () => {
    const full = Array.from({ length: 12 }, (_, index) => `mood${index}`);
    expect(addCustomMood(full, "extra")).toEqual(full);
  });
});
