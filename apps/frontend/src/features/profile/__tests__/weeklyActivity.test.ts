import { describe, expect, it } from "vitest";
import {
  formatPlayedDaysText,
  formatWeeklyCaption,
} from "../lib/weeklyActivity";

describe("weekly activity text", () => {
  it("lists played days with 'and' before the last", () => {
    expect(
      formatPlayedDaysText([true, true, false, false, true, false, false]),
    ).toBe("Played on Monday, Tuesday and Friday this week.");
  });

  it("handles one day", () => {
    expect(
      formatPlayedDaysText([false, false, false, false, false, false, true]),
    ).toBe("Played on Sunday this week.");
  });

  it("uses a quiet message when nothing was played", () => {
    expect(
      formatPlayedDaysText([false, false, false, false, false, false, false]),
    ).toBe("No stories this week yet.");
  });

  it("captions with pluralisation and never uses streak wording", () => {
    expect(formatWeeklyCaption(3)).toBe("Played 3 days this week");
    expect(formatWeeklyCaption(1)).toBe("Played 1 day this week");
    expect(formatWeeklyCaption(0)).toBe("No stories this week yet");
    expect(formatWeeklyCaption(0)).not.toMatch(/streak|broke|miss|lost/i);
  });
});
