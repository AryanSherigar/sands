// Beats are judged on one clock. With audio available that is the audio clock
// (it keeps running steadily under a slow frame rate); without it, the
// performance clock stands in and the game is a visual-only beat.

const MS_PER_SECOND = 1000;

export interface ComposureClock {
  nowMs: () => number;
  // Maps a DOM event's `timeStamp` (performance time) onto this clock.
  fromEventTime: (eventTimeStampMs: number) => number;
  suspend: () => void;
  // Returns how much clock time passed while suspended, so a clock that kept
  // running can have the beat schedule shifted by it.
  resume: () => number;
}

export interface AudioClockSource {
  currentTime: number;
  suspend: () => Promise<void>;
  resume: () => Promise<void>;
}

export function createAudioClock(
  source: AudioClockSource,
  perfNow: () => number = () => performance.now(),
): ComposureClock {
  let offsetMs = perfNow() - source.currentTime * MS_PER_SECOND;
  return {
    nowMs: () => source.currentTime * MS_PER_SECOND,
    fromEventTime: (eventTimeStampMs) => eventTimeStampMs - offsetMs,
    suspend: () => {
      void source.suspend();
    },
    resume: () => {
      void source.resume();
      offsetMs = perfNow() - source.currentTime * MS_PER_SECOND;
      // A suspended audio clock stands still, so nothing needs shifting.
      return 0;
    },
  };
}

export function createPerformanceClock(
  perfNow: () => number = () => performance.now(),
): ComposureClock {
  let suspendedAtMs: number | null = null;
  return {
    nowMs: perfNow,
    fromEventTime: (eventTimeStampMs) => eventTimeStampMs,
    suspend: () => {
      suspendedAtMs = perfNow();
    },
    resume: () => {
      const pausedMs = suspendedAtMs === null ? 0 : perfNow() - suspendedAtMs;
      suspendedAtMs = null;
      return pausedMs;
    },
  };
}
