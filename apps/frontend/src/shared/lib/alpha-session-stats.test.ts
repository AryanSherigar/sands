import { describe, expect, it } from "vitest";
import {
  countSessionEvent,
  createVisibilityTracker,
  drainSessionStats,
  recordUiUsed,
} from "./alpha-session-stats";

describe("alpha-session-stats", () => {
  it("drains counters and ui use, then starts again from zero", () => {
    countSessionEvent("sfx_played_count");
    countSessionEvent("sfx_played_count");
    recordUiUsed("map");
    recordUiUsed("map");
    recordUiUsed("rule_sheet");

    const first = drainSessionStats();
    const second = drainSessionStats();

    expect(first.counters.sfx_played_count).toBe(2);
    expect(first.uiUse).toEqual([
      ["map", 2],
      ["rule_sheet", 1],
    ]);
    expect(second.counters.sfx_played_count).toBe(0);
    expect(second.uiUse).toEqual([]);
  });

  it("splits time between visible and hidden", () => {
    let clock = 0;
    const tracker = createVisibilityTracker("visible", () => clock);

    clock = 4000;
    tracker.update("hidden");
    clock = 5500;
    tracker.update("visible");
    clock = 6000;

    expect(tracker.snapshot()).toEqual({ visible_ms: 4500, hidden_ms: 1500 });
  });
});
