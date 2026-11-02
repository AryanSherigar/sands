import { apiClient } from "@/shared/lib/api-client";
import { logEvent } from "@/shared/lib/logger";
import type { EventNarrativePayload } from "../types/simulation.types";

const TRS_REQUEST_CONFIG = { baseURL: "" };

export async function requestEventNarrative(
  playthroughId: string,
  eventId: string,
): Promise<EventNarrativePayload | null> {
  try {
    const response = await apiClient.post<EventNarrativePayload | null>(
      `/trs/v1/strategy/playthroughs/${playthroughId}/events/${eventId}/narrate`,
      undefined,
      TRS_REQUEST_CONFIG,
    );
    return response.data;
  } catch {
    logEvent("warning", "strategy_event_narrative_request_failed", { eventId });
    return null;
  }
}
