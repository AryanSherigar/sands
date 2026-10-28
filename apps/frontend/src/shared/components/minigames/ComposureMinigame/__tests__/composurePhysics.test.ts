import { describe, expect, it } from "vitest";
import {
  DEFAULT_COMPOSURE_CONFIG,
  type ComposureConfigShape,
} from "@/shared/types/minigame.types";
import {
  INITIAL_RUN,
  advanceRun,
  beatIntervalMs,
  buildBeatSchedule,
  dueMisses,
  effectiveTolerance,
  findPressedBeat,
  judgeKeypress,
  maxBeats,
  nextExpectedKey,
} from "../composurePhysics";

const config = (
  overrides: Partial<ComposureConfigShape> = {},
): ComposureConfigShape => ({ ...DEFAULT_COMPOSURE_CONFIG, ...overrides });

const sequence = (values: number[]) => {
  let index = 0;
  return () => values[index++ % values.length];
};

describe("composure physics", () => {
  it("spaces beats by 60000 / bpm", () => {
    const beats = buildBeatSchedule(config({ target_bpm: 60 }), 1000, () => 0);

    expect(beatIntervalMs(60)).toBe(1000);
    expect(beats[0].timeMs).toBe(1000);
    expect(beats[1].timeMs - beats[0].timeMs).toBe(1000);
  });

  it("schedules exactly as many beats as a run can last", () => {
    const beats = buildBeatSchedule(
      config({ beats_to_win: 4, max_strikes: 3 }),
      0,
      () => 0,
    );

    expect(maxBeats(config({ beats_to_win: 4, max_strikes: 3 }))).toBe(12);
    expect(beats).toHaveLength(12);
  });

  it("draws the expected key from the configured keys only", () => {
    const keys = config({ keys: ["W", "D"] }).keys;

    expect(nextExpectedKey(keys, sequence([0]))).toBe("W");
    expect(nextExpectedKey(keys, sequence([0.99]))).toBe("D");
    expect(nextExpectedKey(keys, sequence([1]))).toBe("D");
  });

  it("is deterministic for a seeded generator", () => {
    const first = buildBeatSchedule(config(), 0, sequence([0.1, 0.4, 0.7, 0.9]));
    const second = buildBeatSchedule(config(), 0, sequence([0.1, 0.4, 0.7, 0.9]));

    expect(first.map((beat) => beat.expectedKey)).toEqual(
      second.map((beat) => beat.expectedKey),
    );
  });

  describe("judgeKeypress", () => {
    it("hits exactly at the tolerance edge", () => {
      expect(judgeKeypress(1000, 1180, 180, "W", "W")).toBe("hit");
      expect(judgeKeypress(1000, 820, 180, "W", "W")).toBe("hit");
    });

    it("misses just outside the tolerance", () => {
      expect(judgeKeypress(1000, 1181, 180, "W", "W")).toBe("miss");
      expect(judgeKeypress(1000, 819, 180, "W", "W")).toBe("miss");
    });

    it("is a wrong key when the timing is right but the key is not", () => {
      expect(judgeKeypress(1000, 1000, 180, "W", "A")).toBe("wrong_key");
    });
  });

  it("widens the tolerance by half when effects are reduced", () => {
    expect(effectiveTolerance(config({ tolerance_ms: 180 }), false)).toBe(180);
    expect(effectiveTolerance(config({ tolerance_ms: 180 }), true)).toBe(270);
  });

  describe("finding the pressed beat", () => {
    const beats = buildBeatSchedule(config({ target_bpm: 120 }), 1000, () => 0);

    it("picks the nearest unresolved beat inside the window", () => {
      expect(findPressedBeat(beats, new Set(), 1490, 180)?.index).toBe(1);
    });

    it("ignores a stray press far from every beat", () => {
      expect(findPressedBeat(beats, new Set(), 1250, 100)).toBeNull();
    });

    it("skips beats that are already resolved", () => {
      expect(findPressedBeat(beats, new Set([0]), 1000, 100)).toBeNull();
    });
  });

  it("reports beats whose window closed unpressed as misses", () => {
    const beats = buildBeatSchedule(config({ target_bpm: 60 }), 1000, () => 0);

    expect(dueMisses(beats, new Set(), 1180, 180)).toHaveLength(0);
    expect(dueMisses(beats, new Set(), 1181, 180).map((b) => b.index)).toEqual([0]);
    expect(dueMisses(beats, new Set([0]), 1181, 180)).toHaveLength(0);
  });

  describe("advanceRun", () => {
    const rules = config({ beats_to_win: 3, max_strikes: 2 });

    it("extends the streak on a hit and tracks the longest", () => {
      const run = advanceRun(advanceRun(INITIAL_RUN, "hit", rules), "hit", rules);

      expect(run).toMatchObject({ streak: 2, longestStreak: 2, outcome: null });
    });

    it("resets the streak on a strike but keeps the longest", () => {
      let run = advanceRun(INITIAL_RUN, "hit", rules);
      run = advanceRun(advanceRun(run, "hit", rules), "strike", rules);

      expect(run).toMatchObject({ streak: 0, strikes: 1, longestStreak: 2 });
    });

    it("wins at beats_to_win consecutive hits", () => {
      let run = INITIAL_RUN;
      for (let i = 0; i < 3; i += 1) run = advanceRun(run, "hit", rules);

      expect(run.outcome).toBe("win");
    });

    it("loses at max_strikes", () => {
      const run = advanceRun(advanceRun(INITIAL_RUN, "strike", rules), "strike", rules);

      expect(run.outcome).toBe("lose");
    });

    it("does not let a strike in between count toward a win", () => {
      let run = INITIAL_RUN;
      for (const event of ["hit", "hit", "strike", "hit", "hit"] as const) {
        run = advanceRun(run, event, rules);
      }

      expect(run.outcome).toBeNull();
    });

    it("ignores events once the run has ended", () => {
      const lost = advanceRun(advanceRun(INITIAL_RUN, "strike", rules), "strike", rules);

      expect(advanceRun(lost, "hit", rules)).toBe(lost);
    });
  });
});
