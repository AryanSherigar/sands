import { useAuthStore } from "@/features/auth/stores/auth.store";
import { TRS_BASE_URL } from "@/shared/constants/api";
import { isAlphaPausedError } from "./alpha-paused-error";
import { isRateLimitError } from "./rate-limit-error";
import {
  generateClientActionId,
  generateRequestId,
  setCurrentRequestId,
} from "./request-id";
import { createPostSSEConnection, type SSEHandlers } from "./sse-client";

const NARRATIVE_ACTION_MODE = "do";
const CONNECTION_LOST_MESSAGE =
  "Connection lost. Your turn may not have saved. You can try again.";
const STREAM_STOPPED_MESSAGE =
  "The narrator stopped responding unexpectedly. Please try again.";

export interface NarrativeTurnRequest {
  playthroughId: string;
  participantId: string;
  actionText: string;
  clientActionId?: string;
}

export interface NarrativeTurnCallbacks {
  onNarration: (chunk: string) => void;
  onDone: () => void;
  onFailure: (message: string) => void;
  onNotice: (message: string) => void;
  onStateUpdate?: (state: Record<string, unknown>) => void;
}

const parseJson = <T>(data: string): T | null => {
  try {
    return JSON.parse(data) as T;
  } catch {
    return null;
  }
};

const buildNotice = (eventName: string, data: string): string | null => {
  if (eventName === "quota_notice") {
    return parseJson<{ detail?: string }>(data)?.detail ?? null;
  }
  const payload = parseJson<{ max_length?: number }>(data);
  if (!payload?.max_length) return null;
  return `Your action was too long, so only the first ${payload.max_length} characters were used.`;
};

const describeError = (error: unknown): string =>
  isRateLimitError(error) || isAlphaPausedError(error)
    ? error.message
    : CONNECTION_LOST_MESSAGE;

const readStateUpdate = (data: string, callbacks: NarrativeTurnCallbacks): void => {
  const payload = parseJson<{ state?: Record<string, unknown> }>(data);
  if (payload?.state) callbacks.onStateUpdate?.(payload.state);
};

const createHandlers = (callbacks: NarrativeTurnCallbacks): SSEHandlers => {
  let hasFinished = false;
  const finish = (action: () => void): void => {
    if (hasFinished) return;
    hasFinished = true;
    action();
  };

  return {
    onEvent: (eventName, data) => {
      if (eventName === "narration") callbacks.onNarration(data);
      else if (eventName === "state_update") readStateUpdate(data, callbacks);
      else if (eventName === "done") finish(callbacks.onDone);
      else if (eventName === "degraded") finish(() => callbacks.onFailure(data));
      else if (eventName === "quota_notice" || eventName === "input_truncated") {
        const notice = buildNotice(eventName, data);
        if (notice) callbacks.onNotice(notice);
      }
    },
    onError: (error) => finish(() => callbacks.onFailure(describeError(error))),
    onClose: () => finish(() => callbacks.onFailure(STREAM_STOPPED_MESSAGE)),
  };
};

export const startNarrativeTurn = (
  request: NarrativeTurnRequest,
  callbacks: NarrativeTurnCallbacks,
): (() => void) => {
  const requestId = generateRequestId();
  setCurrentRequestId(requestId);
  const body = {
    playthrough_id: request.playthroughId,
    participant_id: request.participantId,
    client_action_id: request.clientActionId ?? generateClientActionId(),
    action_text: request.actionText,
    action_kind: "narrative",
    action_mode: NARRATIVE_ACTION_MODE,
    voice_output_requested: false,
  };
  return createPostSSEConnection(
    `${TRS_BASE_URL}/v1/turn`,
    body,
    useAuthStore.getState().accessToken,
    createHandlers(callbacks),
    requestId,
  );
};
