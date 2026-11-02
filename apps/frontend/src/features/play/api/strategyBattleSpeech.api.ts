import { apiClient } from "@/shared/lib/api-client";
import { logEvent } from "@/shared/lib/logger";
import type { SpeechReactionPayload } from "../types/simulation.types";

const TRS_REQUEST_CONFIG = { baseURL: "" };

export async function requestSpeechReaction(
  playthroughId: string,
  battleId: string,
): Promise<string | null> {
  try {
    const response = await apiClient.post<SpeechReactionPayload | null>(
      `/trs/v1/strategy/playthroughs/${playthroughId}/battles/${battleId}/speech/reaction`,
      undefined,
      TRS_REQUEST_CONFIG,
    );
    return response.data?.line ?? null;
  } catch {
    logEvent("warning", "battle_speech_reaction_request_failed", { battleId });
    return null;
  }
}
