import type { ComposureConfigShape, ComposureKey } from "@/shared/types/minigame.types";
import type { ComposureAudioPort } from "./composureAudio";
import type { ComposureClock } from "./composureClock";
import {
  INITIAL_RUN,
  advanceRun,
  beatIntervalMs,
  buildBeatSchedule,
  dueMisses,
  effectiveTolerance,
  findPressedBeat,
  judgeKeypress,
  type Beat,
  type BeatEvent,
  type RunState,
} from "./composurePhysics";

const MS_PER_SECOND = 1000;
export const LEAD_IN_MS = 1500;
export const LOOKAHEAD_MS = 400;

export interface ComposureResult {
  outcome_tag: "win" | "lose";
  score: number;
}

export interface ComposureFeedback {
  kind: BeatEvent;
  atMs: number;
}

export interface ComposureView {
  nowMs: number;
  nextBeat: Beat | null;
  intervalMs: number;
  run: RunState;
  feedback: ComposureFeedback | null;
}

export interface ComposureEngineOptions {
  config: ComposureConfigShape;
  clock: ComposureClock;
  audio: ComposureAudioPort | null;
  rng: () => number;
  isReduced: boolean;
  onChange: (run: RunState, feedback: ComposureFeedback | null) => void;
  onFinish: (result: ComposureResult) => void;
}

// The rules of the game with no DOM and no timers of its own: the loop hook
// calls `tick` every frame and forwards key presses, so it runs under a fake
// clock in tests.
export class ComposureEngine {
  private beats: Beat[] = [];
  private readonly resolved = new Set<number>();
  private readonly scheduledAudio = new Set<number>();
  private run: RunState = INITIAL_RUN;
  private feedback: ComposureFeedback | null = null;
  private isPaused = false;
  private isStarted = false;
  private readonly toleranceMs: number;

  constructor(private readonly options: ComposureEngineOptions) {
    this.toleranceMs = effectiveTolerance(options.config, options.isReduced);
  }

  public start(): void {
    const firstBeatMs = this.options.clock.nowMs() + LEAD_IN_MS;
    this.beats = buildBeatSchedule(this.options.config, firstBeatMs, this.options.rng);
    this.isStarted = true;
  }

  public tick(): void {
    if (!this.isActive()) return;
    const nowMs = this.options.clock.nowMs();
    this.scheduleAudioAhead(nowMs);
    for (const beat of dueMisses(this.beats, this.resolved, nowMs, this.toleranceMs)) {
      this.resolve(beat, "strike", nowMs);
      if (!this.isActive()) return;
    }
  }

  public pressKey(key: ComposureKey, eventTimeStampMs: number): BeatEvent | null {
    if (!this.isActive()) return null;
    const pressMs = this.options.clock.fromEventTime(eventTimeStampMs);
    const beat = findPressedBeat(this.beats, this.resolved, pressMs, this.toleranceMs);
    if (beat === null) return null;
    const judgement = judgeKeypress(
      beat.timeMs,
      pressMs,
      this.toleranceMs,
      beat.expectedKey,
      key,
    );
    const event: BeatEvent = judgement === "hit" ? "hit" : "strike";
    this.resolve(beat, event, this.options.clock.nowMs());
    return event;
  }

  public pause(): void {
    if (!this.isActive()) return;
    this.isPaused = true;
    this.options.clock.suspend();
  }

  public resume(): void {
    if (!this.isPaused) return;
    const shiftMs = this.options.clock.resume();
    this.beats = this.beats.map((beat) => ({ ...beat, timeMs: beat.timeMs + shiftMs }));
    this.isPaused = false;
  }

  public getView(): ComposureView {
    const nowMs = this.options.clock.nowMs();
    const nextBeat = this.beats.find((beat) => !this.resolved.has(beat.index)) ?? null;
    return {
      nowMs,
      nextBeat,
      intervalMs: beatIntervalMs(this.options.config.target_bpm),
      run: this.run,
      feedback: this.feedback,
    };
  }

  private isActive(): boolean {
    return this.isStarted && !this.isPaused && this.run.outcome === null;
  }

  private resolve(beat: Beat, event: BeatEvent, nowMs: number): void {
    this.resolved.add(beat.index);
    this.run = advanceRun(this.run, event, this.options.config);
    this.feedback = { kind: event, atMs: nowMs };
    if (event === "hit") this.options.audio?.playHit();
    else this.options.audio?.playStrike();
    this.options.onChange(this.run, this.feedback);
    if (this.run.outcome !== null) this.finish(this.run.outcome);
  }

  private finish(outcome: "win" | "lose"): void {
    this.options.audio?.playOutcome(outcome);
    this.options.onFinish({ outcome_tag: outcome, score: this.run.longestStreak });
  }

  private scheduleAudioAhead(nowMs: number): void {
    const audio = this.options.audio;
    if (audio === null) return;
    for (const beat of this.beats) {
      if (this.scheduledAudio.has(beat.index) || beat.timeMs - nowMs > LOOKAHEAD_MS) {
        continue;
      }
      this.scheduledAudio.add(beat.index);
      audio.scheduleBeat(beat.timeMs / MS_PER_SECOND, this.run.strikes);
    }
  }
}
