import { emitAlphaEvent } from "@/shared/lib/alpha-events";
import { countSessionEvent } from "@/shared/lib/alpha-session-stats";
import type { TurnRetryKind } from "@/shared/types/alphaEvents.types";

export interface TurnStreamTelemetry {
  markFirstToken: () => void;
  recordDone: () => void;
  recordStall: () => void;
}

let lastStallAt: number | null = null;

interface TurnCountSource {
  turns?: readonly unknown[];
}

export function nextTurnNumber(playthrough: TurnCountSource | null | undefined): number {
  return (playthrough?.turns?.length ?? 0) + 1;
}

export function startTurnStreamTelemetry(
  turnNumber: number,
  playthroughId: string | undefined,
  isRecovery: boolean,
): TurnStreamTelemetry {
  const startedAt = performance.now();
  let firstTokenMs: number | null = null;
  const options = { playthroughId };

  if (isRecovery && lastStallAt !== null) {
    emitAlphaEvent(
      "stream_reconnect",
      { turn_number: turnNumber, stalled_ms: Math.round(startedAt - lastStallAt) },
      options,
    );
  }

  return {
    markFirstToken: () => {
      firstTokenMs ??= Math.round(performance.now() - startedAt);
    },
    recordDone: () => {
      lastStallAt = null;
      countSessionEvent("turns_in_session");
      emitAlphaEvent(
        "turn_perceived_latency",
        {
          turn_number: turnNumber,
          first_token_ms: firstTokenMs,
          total_ms: Math.round(performance.now() - startedAt),
        },
        options,
      );
    },
    recordStall: () => {
      const now = performance.now();
      lastStallAt = now;
      emitAlphaEvent(
        "stream_stall",
        { turn_number: turnNumber, stalled_ms: Math.round(now - startedAt) },
        options,
      );
    },
  };
}

export function emitTurnRetry(
  kind: TurnRetryKind,
  turnNumber: number,
  clientActionId: string,
  playthroughId: string | undefined,
): void {
  emitAlphaEvent(
    "turn_retry",
    { kind, turn_number: turnNumber, client_action_id: clientActionId },
    { playthroughId },
  );
}
