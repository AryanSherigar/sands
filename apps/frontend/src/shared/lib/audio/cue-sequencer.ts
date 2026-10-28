import { SensoryCueId } from "@/shared/constants/sensory-cues";

export interface QueuedCue {
  cue: SensoryCueId;
  cut_ambient: boolean;
  silence_duration_ms: number;
}

export interface CueSequencerAudio {
  hardMute: (durationMs?: number) => void;
  playSfx: (
    cue: SensoryCueId,
    options: { leadSilenceMs: number },
  ) => Promise<void>;
  resumeAmbient: (rampMs: number) => void;
}

const HARD_CUT_MS = 30;
const AMBIENT_RESUME_RAMP_MS = 1500;

// Runs queued cues one at a time, first in first out: hard cut, dead air, the
// sound, then the ambience returns. A burst of cues cuts once and resumes once.
export class CueSequencer {
  private readonly queue: QueuedCue[] = [];
  private isRunning = false;
  private isCancelled = false;
  private readonly idleWaiters: (() => void)[] = [];

  constructor(private readonly audio: CueSequencerAudio) {}

  public enqueue(cue: QueuedCue): void {
    this.isCancelled = false;
    this.queue.push(cue);
    if (!this.isRunning) void this.run();
  }

  /** Resolves once no cue sequence is running, so a mood change that arrives
   * during one can wait for the ambience to come back first. */
  public whenIdle(): Promise<void> {
    if (!this.isRunning) return Promise.resolve();
    return new Promise((resolve) => this.idleWaiters.push(resolve));
  }

  public cancel(): void {
    this.isCancelled = true;
    this.queue.length = 0;
  }

  private async run(): Promise<void> {
    this.isRunning = true;
    let isCut = false;
    try {
      let next = this.queue.shift();
      while (next) {
        let leadSilenceMs = 0;
        if (next.cut_ambient && !isCut) {
          this.audio.hardMute(HARD_CUT_MS);
          isCut = true;
          leadSilenceMs = next.silence_duration_ms;
        }
        await this.audio.playSfx(next.cue, { leadSilenceMs });
        next = this.isCancelled ? undefined : this.queue.shift();
      }
    } catch {
      // A sound that cannot play must never leave the ambience cut.
    } finally {
      if (isCut) this.audio.resumeAmbient(AMBIENT_RESUME_RAMP_MS);
      this.isRunning = false;
      for (const resolve of this.idleWaiters.splice(0)) resolve();
    }
  }
}
