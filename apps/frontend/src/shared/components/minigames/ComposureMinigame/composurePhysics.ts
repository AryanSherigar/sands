import type {
  ComposureConfigShape,
  ComposureKey,
  MinigameOutcomeTag,
} from "@/shared/types/minigame.types";

const MS_PER_MINUTE = 60_000;
const REDUCED_TOLERANCE_FACTOR = 1.5;

export type KeyJudgement = "hit" | "wrong_key" | "miss";
export type BeatEvent = "hit" | "strike";

export interface Beat {
  index: number;
  timeMs: number;
  expectedKey: ComposureKey;
}

export interface RunState {
  streak: number;
  strikes: number;
  longestStreak: number;
  outcome: Exclude<MinigameOutcomeTag, "timeout"> | null;
}

export const INITIAL_RUN: RunState = {
  streak: 0,
  strikes: 0,
  longestStreak: 0,
  outcome: null,
};

export const beatIntervalMs = (bpm: number): number => MS_PER_MINUTE / bpm;

// The most beats a run can last: every strike resets the streak, so the game
// ends within `max_strikes` runs of `beats_to_win` beats.
export const maxBeats = (config: ComposureConfigShape): number =>
  config.beats_to_win * config.max_strikes;

export const effectiveTolerance = (
  config: ComposureConfigShape,
  isReduced: boolean,
): number =>
  isReduced
    ? config.tolerance_ms * REDUCED_TOLERANCE_FACTOR
    : config.tolerance_ms;

export const nextExpectedKey = (
  keys: ComposureKey[],
  rng: () => number,
): ComposureKey => keys[Math.min(keys.length - 1, Math.floor(rng() * keys.length))];

export function buildBeatSchedule(
  config: ComposureConfigShape,
  firstBeatMs: number,
  rng: () => number,
): Beat[] {
  const interval = beatIntervalMs(config.target_bpm);
  return Array.from({ length: maxBeats(config) }, (_, index) => ({
    index,
    timeMs: firstBeatMs + index * interval,
    expectedKey: nextExpectedKey(config.keys, rng),
  }));
}

// A press within tolerance of the beat is judged by its key; one outside every
// window never reaches here (see findPressedBeat) and a beat nobody pressed is
// judged "miss" by the engine when its window closes.
export function judgeKeypress(
  beatTimeMs: number,
  pressTimeMs: number,
  toleranceMs: number,
  expected: ComposureKey,
  pressed: ComposureKey,
): KeyJudgement {
  if (Math.abs(pressTimeMs - beatTimeMs) > toleranceMs) return "miss";
  return pressed === expected ? "hit" : "wrong_key";
}

export function findPressedBeat(
  beats: Beat[],
  resolved: ReadonlySet<number>,
  pressTimeMs: number,
  toleranceMs: number,
): Beat | null {
  let nearest: Beat | null = null;
  for (const beat of beats) {
    if (resolved.has(beat.index)) continue;
    const distance = Math.abs(pressTimeMs - beat.timeMs);
    const isCloser =
      nearest === null || distance < Math.abs(pressTimeMs - nearest.timeMs);
    if (distance <= toleranceMs && isCloser) nearest = beat;
  }
  return nearest;
}

export function dueMisses(
  beats: Beat[],
  resolved: ReadonlySet<number>,
  nowMs: number,
  toleranceMs: number,
): Beat[] {
  return beats.filter(
    (beat) => !resolved.has(beat.index) && nowMs > beat.timeMs + toleranceMs,
  );
}

// A hit extends the streak; a strike resets it. `beats_to_win` hits in a row
// wins, `max_strikes` strikes loses.
export function advanceRun(
  run: RunState,
  event: BeatEvent,
  config: ComposureConfigShape,
): RunState {
  if (run.outcome !== null) return run;
  if (event === "hit") {
    const streak = run.streak + 1;
    return {
      ...run,
      streak,
      longestStreak: Math.max(run.longestStreak, streak),
      outcome: streak >= config.beats_to_win ? "win" : null,
    };
  }
  const strikes = run.strikes + 1;
  return {
    ...run,
    streak: 0,
    strikes,
    outcome: strikes >= config.max_strikes ? "lose" : null,
  };
}
