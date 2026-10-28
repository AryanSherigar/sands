export const SCENE_MESSAGE_MAX_CHARS = 600;
export const NEGOTIATION_SCENE_TYPE = "negotiation";
export const AI_INITIATOR = "ai";
export const SCENE_STREAM_FAILURE_MESSAGE =
  "The scene could not continue. Your message was not recorded.";
export const SCENE_CONNECTION_LOST_MESSAGE =
  "Connection lost. Your message may not have been recorded.";
export const SCENE_STREAM_STOPPED_MESSAGE =
  "The ruler stopped responding. Please try again.";
export const OPEN_NEGOTIATION_FALLBACK_MESSAGE = "Could not open the negotiation";
export const SCENE_DECISION_FALLBACK_MESSAGE = "Could not record your decision";
export const TERMS_CHANGED_CODE = "terms_changed";
export const TERMS_CHANGED_MESSAGE =
  "The terms changed while you were reading. Review the updated card before signing.";
export const FINAL_SCENE_STATUSES: readonly string[] = ["resolved", "defaulted"];

export const getSceneQueryKey = (playthroughId?: string, sceneId?: string | null) =>
  ["simulation-scene", playthroughId, sceneId] as const;
