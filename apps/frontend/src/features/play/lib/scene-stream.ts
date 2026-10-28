import { useAuthStore } from "@/features/auth/stores/auth.store";
import { TRS_BASE_URL } from "@/shared/constants/api";
import { isAlphaPausedError } from "@/shared/lib/alpha-paused-error";
import { isRateLimitError } from "@/shared/lib/rate-limit-error";
import { generateRequestId, setCurrentRequestId } from "@/shared/lib/request-id";
import { createPostSSEConnection, type SSEHandlers } from "@/shared/lib/sse-client";
import {
  SCENE_CONNECTION_LOST_MESSAGE,
  SCENE_STREAM_STOPPED_MESSAGE,
} from "../constants/scene.constants";

export interface SceneMessageCallbacks {
  onNarration: (chunk: string) => void;
  onDone: () => void;
  onFailure: (message: string) => void;
}

const describeError = (error: unknown): string =>
  isRateLimitError(error) || isAlphaPausedError(error)
    ? error.message
    : SCENE_CONNECTION_LOST_MESSAGE;

const createHandlers = (callbacks: SceneMessageCallbacks): SSEHandlers => {
  let hasFinished = false;
  const finish = (action: () => void): void => {
    if (hasFinished) return;
    hasFinished = true;
    action();
  };

  return {
    onEvent: (eventName, data) => {
      if (eventName === "narration") callbacks.onNarration(data);
      else if (eventName === "done") finish(callbacks.onDone);
      else if (eventName === "degraded") finish(() => callbacks.onFailure(data));
    },
    onError: (error) => finish(() => callbacks.onFailure(describeError(error))),
    onClose: () => finish(() => callbacks.onFailure(SCENE_STREAM_STOPPED_MESSAGE)),
  };
};

export const startSceneMessage = (
  sceneId: string,
  text: string,
  callbacks: SceneMessageCallbacks,
): (() => void) => {
  const requestId = generateRequestId();
  setCurrentRequestId(requestId);
  return createPostSSEConnection(
    `${TRS_BASE_URL}/v1/scenes/${sceneId}/messages`,
    { text },
    useAuthStore.getState().accessToken,
    createHandlers(callbacks),
    requestId,
  );
};
