import { emitAlphaEvent } from "./alpha-events";
import { countSessionEvent } from "./alpha-session-stats";
import type { AudioBlockedProps } from "@/shared/types/alphaEvents.types";

const AUTOPLAY_BLOCKED_ERROR_NAME = "NotAllowedError";

export function recordAudioBlocked(reason: AudioBlockedProps["reason"]): void {
  countSessionEvent("audio_blocked_count");
  emitAlphaEvent("audio_blocked", { reason });
}

export function recordPlayRejected(error: unknown): void {
  const isAutoplayBlock =
    error instanceof DOMException && error.name === AUTOPLAY_BLOCKED_ERROR_NAME;
  recordAudioBlocked(isAutoplayBlock ? "autoplay_policy" : "error");
}

export function recordSfxPlayed(): void {
  countSessionEvent("sfx_played_count");
}
