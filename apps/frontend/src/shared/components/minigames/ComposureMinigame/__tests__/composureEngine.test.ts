import { describe, expect, it, vi } from "vitest";
import {
  DEFAULT_COMPOSURE_CONFIG,
  type ComposureConfigShape,
} from "@/shared/types/minigame.types";
import type { ComposureAudioPort } from "../composureAudio";
import type { ComposureClock } from "../composureClock";
import {
  ComposureEngine,
  LEAD_IN_MS,
  LOOKAHEAD_MS,
  type ComposureResult,
} from "../composureEngine";

const config = (
  overrides: Partial<ComposureConfigShape> = {},
): ComposureConfigShape => ({
  ...DEFAULT_COMPOSURE_CONFIG,
  target_bpm: 60,
  beats_to_win: 3,
  max_strikes: 2,
  tolerance_ms: 200,
  keys: ["W"],
  ...overrides,
});

const makeClock = () => {
  const state = { now: 0, shift: 0, suspended: 0 };
  const clock: ComposureClock = {
    nowMs: () => state.now,
    fromEventTime: (stamp) => stamp,
    suspend: () => {
      state.suspended += 1;
    },
    resume: () => state.shift,
  };
  return { state, clock };
};

const makeAudio = () => ({
  scheduleBeat: vi.fn<ComposureAudioPort["scheduleBeat"]>(),
  playHit: vi.fn<ComposureAudioPort["playHit"]>(),
  playStrike: vi.fn<ComposureAudioPort["playStrike"]>(),
  playOutcome: vi.fn<ComposureAudioPort["playOutcome"]>(),
});

const setup = (
  overrides: Partial<ComposureConfigShape> = {},
  isReduced = false,
  withAudio = true,
) => {
  const { state, clock } = makeClock();
  const audio = makeAudio();
  const results: ComposureResult[] = [];
  const onChange = vi.fn();
  const engine = new ComposureEngine({
    config: config(overrides),
    clock,
    audio: withAudio ? audio : null,
    rng: () => 0,
    isReduced,
    onChange,
    onFinish: (result) => results.push(result),
  });
  engine.start();
  return { engine, state, audio, results, onChange };
};

const firstBeat = LEAD_IN_MS;
const second = (index: number): number => firstBeat + index * 1000;

describe("ComposureEngine", () => {
  it("starts the first beat after the lead-in", () => {
    const { engine } = setup();

    expect(engine.getView().nextBeat?.timeMs).toBe(firstBeat);
  });

  it("counts a keypress on the beat as a hit", () => {
    const { engine, state } = setup();
    state.now = firstBeat;

    expect(engine.pressKey("W", firstBeat + 50)).toBe("hit");
    expect(engine.getView().run.streak).toBe(1);
  });

  it("counts the wrong key within the window as a strike", () => {
    const { engine, state } = setup({ keys: ["W", "A"] });
    state.now = firstBeat;
    const expected = engine.getView().nextBeat!.expectedKey;
    const wrong = expected === "W" ? "A" : "W";

    expect(engine.pressKey(wrong, firstBeat)).toBe("strike");
    expect(engine.getView().run.strikes).toBe(1);
  });

  it("ignores a stray press far from any beat", () => {
    const { engine, state } = setup();
    state.now = 200;

    expect(engine.pressKey("W", 200)).toBeNull();
    expect(engine.getView().run.strikes).toBe(0);
  });

  it("strikes a beat nobody pressed once its window has closed", () => {
    const { engine, state } = setup();
    state.now = firstBeat + 201;

    engine.tick();

    expect(engine.getView().run.strikes).toBe(1);
  });

  it("does not strike a beat that is still inside its window", () => {
    const { engine, state } = setup();
    state.now = firstBeat + 200;

    engine.tick();

    expect(engine.getView().run.strikes).toBe(0);
  });

  it("wins after beats_to_win consecutive hits and reports the longest streak", () => {
    const { engine, state, results, audio } = setup();
    for (let i = 0; i < 3; i += 1) {
      state.now = second(i);
      engine.pressKey("W", second(i));
    }

    expect(results).toEqual([{ outcome_tag: "win", score: 3 }]);
    expect(audio.playOutcome).toHaveBeenCalledWith("win");
  });

  it("loses at max_strikes", () => {
    const { engine, state, results } = setup();
    state.now = second(5);

    engine.tick();

    expect(results).toEqual([{ outcome_tag: "lose", score: 0 }]);
  });

  it("resets the streak on a strike so the win has to be earned in a row", () => {
    const { engine, state, results } = setup({ max_strikes: 3 });
    state.now = second(0);
    engine.pressKey("W", second(0));
    state.now = second(1) + 300;
    engine.tick();
    for (const index of [2, 3]) {
      state.now = second(index);
      engine.pressKey("W", second(index));
    }

    expect(results).toHaveLength(0);
    expect(engine.getView().run.streak).toBe(2);
  });

  it("ignores everything once finished", () => {
    const { engine, state, results } = setup();
    state.now = second(5);
    engine.tick();

    expect(engine.pressKey("W", second(5))).toBeNull();
    expect(results).toHaveLength(1);
  });

  it("schedules audio only for beats inside the lookahead, once each", () => {
    const { engine, state, audio } = setup();

    state.now = firstBeat - LOOKAHEAD_MS - 1;
    engine.tick();
    expect(audio.scheduleBeat).not.toHaveBeenCalled();

    state.now = firstBeat - LOOKAHEAD_MS;
    engine.tick();
    engine.tick();
    expect(audio.scheduleBeat).toHaveBeenCalledTimes(1);
    expect(audio.scheduleBeat).toHaveBeenCalledWith(firstBeat / 1000, 0);
  });

  it("plays a hit hum and a strike gasp", () => {
    const { engine, state, audio } = setup({ max_strikes: 5 });
    state.now = second(0);
    engine.pressKey("W", second(0));
    state.now = second(1) + 300;
    engine.tick();

    expect(audio.playHit).toHaveBeenCalledTimes(1);
    expect(audio.playStrike).toHaveBeenCalledTimes(1);
  });

  it("runs as a visual-only beat when audio is unavailable", () => {
    const { engine, state } = setup({}, false, false);
    state.now = firstBeat;

    expect(engine.pressKey("W", firstBeat)).toBe("hit");
  });

  it("widens the window by half with reduced effects", () => {
    const strict = setup();
    const reduced = setup({}, true);
    strict.state.now = firstBeat + 250;
    reduced.state.now = firstBeat + 250;

    expect(strict.engine.pressKey("W", firstBeat + 250)).toBeNull();
    expect(reduced.engine.pressKey("W", firstBeat + 250)).toBe("hit");
  });

  describe("pausing", () => {
    it("never counts a paused period as a strike", () => {
      const { engine, state } = setup();
      engine.pause();
      state.now = second(10);

      engine.tick();

      expect(engine.getView().run.strikes).toBe(0);
    });

    it("ignores presses while paused", () => {
      const { engine, state } = setup();
      engine.pause();
      state.now = firstBeat;

      expect(engine.pressKey("W", firstBeat)).toBeNull();
    });

    it("suspends the clock on pause", () => {
      const { engine, state } = setup();

      engine.pause();

      expect(state.suspended).toBe(1);
    });

    it("shifts the schedule by the paused time when the clock kept running", () => {
      const { engine, state } = setup();
      engine.pause();
      state.now = 5000;
      state.shift = 5000;

      engine.resume();

      expect(engine.getView().nextBeat?.timeMs).toBe(firstBeat + 5000);
    });

    it("resumes judging after a pause", () => {
      const { engine, state } = setup();
      engine.pause();
      engine.resume();
      state.now = firstBeat;

      expect(engine.pressKey("W", firstBeat)).toBe("hit");
    });
  });
});
