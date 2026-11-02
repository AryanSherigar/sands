import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { requestEventNarrative } from "../api/strategyEvents.api";
import type {
  CampaignWorldView,
  EventNarrativePayload,
  PendingEventView,
} from "../types/simulation.types";
import { getWorldQueryKey } from "./useSimulationCommands";

function withNarrative(
  world: CampaignWorldView | undefined,
  eventId: string,
  narrative: EventNarrativePayload,
): CampaignWorldView | undefined {
  if (!world?.pending_events) return world;
  return {
    ...world,
    pending_events: world.pending_events.map((event) =>
      event.id === eventId ? { ...event, narrative } : event,
    ),
  };
}

export function usePendingEventNarratives(
  playthroughId: string | undefined,
  events: PendingEventView[] | undefined,
): void {
  const queryClient = useQueryClient();
  const requestedIds = useRef(new Set<string>());

  useEffect(() => {
    if (!playthroughId || !events) return;
    const missing = events.filter(
      (event) => !event.narrative && !requestedIds.current.has(event.id),
    );
    missing.forEach((event) => {
      requestedIds.current.add(event.id);
      void requestEventNarrative(playthroughId, event.id).then((narrative) => {
        if (!narrative) {
          requestedIds.current.delete(event.id);
          return;
        }
        queryClient.setQueryData<CampaignWorldView | undefined>(
          getWorldQueryKey(playthroughId),
          (current) => withNarrative(current, event.id, narrative),
        );
      });
    });
  }, [playthroughId, events, queryClient]);
}
