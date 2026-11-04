import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getStrategyEpilogue, getStrategyEpilogueStreamPath } from "../api/simulation.api";
import { generateClientActionId } from "@/shared/lib/request-id";
import { usePostSSE } from "@/shared/hooks/usePostSSE";

export type StrategyEpilogueStatus = "pending" | "streaming" | "completed" | "failed";

export interface UseStrategyEpilogueReturn {
  narration: string;
  status: StrategyEpilogueStatus;
  errorMessage: string | null;
  start: () => void;
}

const FALLBACK_ERROR_MESSAGE = "The closing entry could not be written. Try again.";

export const getStrategyEpilogueQueryKey = (playthroughId?: string) =>
  ["strategy-epilogue", playthroughId] as const;

function parseErrorMessage(data: string): string {
  try {
    const payload = JSON.parse(data) as { message?: string };
    return payload.message ?? FALLBACK_ERROR_MESSAGE;
  } catch {
    return FALLBACK_ERROR_MESSAGE;
  }
}

export function useStrategyEpilogue(playthroughId?: string): UseStrategyEpilogueReturn {
  const queryClient = useQueryClient();
  const saved = useQuery({
    queryKey: getStrategyEpilogueQueryKey(playthroughId),
    queryFn: () => {
      if (!playthroughId) throw new Error("Playthrough ID is required");
      return getStrategyEpilogue(playthroughId);
    },
    enabled: Boolean(playthroughId),
    staleTime: 0,
  });
  const [streamed, setStreamed] = useState<string | null>(null);
  const [isStreamDone, setIsStreamDone] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const stream = usePostSSE({
    onEvent: (name, data) => {
      if (name === "narration") setStreamed((current) => (current ?? "") + data);
      if (name === "epilogue_error") setErrorMessage(parseErrorMessage(data));
      if (name === "done") {
        setIsStreamDone(true);
        void queryClient.invalidateQueries({ queryKey: getStrategyEpilogueQueryKey(playthroughId) });
      }
    },
    onError: () => setErrorMessage(FALLBACK_ERROR_MESSAGE),
  });

  const start = useCallback(() => {
    if (!playthroughId) return;
    setErrorMessage(null);
    setIsStreamDone(false);
    setStreamed("");
    stream.start(getStrategyEpilogueStreamPath(playthroughId), {
      client_request_id: generateClientActionId(),
    });
  }, [playthroughId, stream]);

  const narration = streamed ?? saved.data?.narration ?? "";
  return { narration, status: deriveStatus(saved.data?.status, streamed, isStreamDone, errorMessage), errorMessage, start };
}

function deriveStatus(
  savedStatus: string | undefined,
  streamed: string | null,
  isStreamDone: boolean,
  errorMessage: string | null,
): StrategyEpilogueStatus {
  if (errorMessage) return "failed";
  if (isStreamDone || savedStatus === "completed") return "completed";
  if (streamed !== null) return "streaming";
  return "pending";
}
