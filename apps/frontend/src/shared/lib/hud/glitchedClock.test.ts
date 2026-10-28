import { describe, expect, it } from "vitest";
import { glitchedClock } from "./glitchedClock";

const glitch = { source: "sanity", below: 25, chance: 0.02 };

const base = { playthroughId: "pt-1", glitch, sourceValue: 10 };

const glitchedMinutes = (chance: number, count: number): number[] =>
  Array.from({ length: count }, (_, minutes) => minutes).filter(
    (minutes) =>
      glitchedClock({
        ...base,
        glitch: { ...glitch, chance },
        displayedMinutes: minutes,
      }) !== null,
  );

describe("glitchedClock", () => {
  it("is deterministic for a minute value", () => {
    const first = glitchedMinutes(0.5, 200);
    expect(glitchedMinutes(0.5, 200)).toEqual(first);
    expect(first.length).toBeGreaterThan(0);
  });

  it("returns an impossible minute between 60 and 99", () => {
    for (const minutes of glitchedMinutes(1, 100)) {
      const value = glitchedClock({
        ...base,
        glitch: { ...glitch, chance: 1 },
        displayedMinutes: minutes,
      });
      expect(value).toBeGreaterThanOrEqual(60);
      expect(value).toBeLessThanOrEqual(99);
    }
  });

  it("glitches about `chance` of the minutes", () => {
    const hits = glitchedMinutes(0.1, 3000).length;
    expect(hits).toBeGreaterThan(220);
    expect(hits).toBeLessThan(380);
  });

  it("never glitches at or above the threshold", () => {
    for (let minutes = 0; minutes < 200; minutes += 1) {
      expect(
        glitchedClock({
          ...base,
          glitch: { ...glitch, chance: 1 },
          sourceValue: 25,
          displayedMinutes: minutes,
        }),
      ).toBeNull();
    }
  });

  it("is disabled without a glitch rule or a numeric source", () => {
    const always = { ...base, displayedMinutes: 5 };
    expect(glitchedClock({ ...always, glitch: undefined })).toBeNull();
    expect(glitchedClock({ ...always, sourceValue: undefined })).toBeNull();
    expect(glitchedClock({ ...always, sourceValue: "low" })).toBeNull();
  });
});
