import type { AlphaUiFeature } from "@/shared/types/alphaEvents.types";

export interface SessionCounters {
  sfx_played_count: number;
  audio_blocked_count: number;
  turns_in_session: number;
}

function emptyCounters(): SessionCounters {
  return { sfx_played_count: 0, audio_blocked_count: 0, turns_in_session: 0 };
}

let counters = emptyCounters();
let uiUseCounts = new Map<AlphaUiFeature, number>();

export function countSessionEvent(counter: keyof SessionCounters): void {
  counters[counter] += 1;
}

export function recordUiUsed(feature: AlphaUiFeature): void {
  uiUseCounts.set(feature, (uiUseCounts.get(feature) ?? 0) + 1);
}

export function drainSessionStats(): {
  counters: SessionCounters;
  uiUse: Array<[AlphaUiFeature, number]>;
} {
  const drained = { counters, uiUse: [...uiUseCounts.entries()] };
  counters = emptyCounters();
  uiUseCounts = new Map();
  return drained;
}

interface VisibilityTotals {
  visible_ms: number;
  hidden_ms: number;
}

export interface VisibilityTracker {
  update: (next: DocumentVisibilityState) => void;
  snapshot: () => VisibilityTotals;
}

export function createVisibilityTracker(
  initialState: DocumentVisibilityState,
  now: () => number = () => performance.now(),
): VisibilityTracker {
  let state = initialState;
  let lastChange = now();
  const totals: VisibilityTotals = { visible_ms: 0, hidden_ms: 0 };

  const settle = (): void => {
    const current = now();
    const key = state === "visible" ? "visible_ms" : "hidden_ms";
    totals[key] += current - lastChange;
    lastChange = current;
  };

  return {
    update: (next) => {
      settle();
      state = next;
    },
    snapshot: () => {
      settle();
      return {
        visible_ms: Math.round(totals.visible_ms),
        hidden_ms: Math.round(totals.hidden_ms),
      };
    },
  };
}
