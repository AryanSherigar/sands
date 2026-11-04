export const MAX_SPEECH_TALKS = 3;
export const SPEECH_NOT_FOUND_STATUS = 404;
export const BATTLE_SPEECH_QUERY_ROOT = "battle-speech";

export const getBattleSpeechQueryKey = (playthroughId?: string, battleId?: string | null) =>
  [BATTLE_SPEECH_QUERY_ROOT, playthroughId, battleId] as const;
