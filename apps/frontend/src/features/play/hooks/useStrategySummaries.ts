import { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getStrategySummaries,
  getStrategySummary,
  getStrategySummaryStreamPath,
} from "../api/simulation.api";
import type { StrategySummaryView } from "../types/simulation.types";
import { generateClientActionId } from "@/shared/lib/request-id";
import { usePostSSE } from "@/shared/hooks/usePostSSE";

export const getStrategySummariesQueryKey = (playthroughId?: string) =>
  ["strategy-summaries", playthroughId] as const;

const summaryQueryKey = (playthroughId: string, summaryId: string) =>
  ["strategy-summary", playthroughId, summaryId] as const;

interface SummaryStreamError {
  code: string;
  message: string;
  is_retryable: boolean;
}

function parseStreamError(data: string): SummaryStreamError {
  try {
    return JSON.parse(data) as SummaryStreamError;
  } catch {
    return { code: "summary_unavailable", message: "Chronicle could not be loaded. Try again.", is_retryable: true };
  }
}

function summaryIdFromDone(data: string): string | null {
  try {
    const payload = JSON.parse(data) as { summary_id?: string };
    return payload.summary_id ?? null;
  } catch {
    return null;
  }
}

export function useStrategySummaries(playthroughId?: string) {
  return useQuery({
    queryKey: getStrategySummariesQueryKey(playthroughId),
    queryFn: () => {
      if (!playthroughId) throw new Error("Playthrough ID is required");
      return getStrategySummaries(playthroughId);
    },
    enabled: Boolean(playthroughId),
    staleTime: 0,
  });
}

export function useStrategySummary(playthroughId?: string, summaryId?: string) {
  return useQuery({
    queryKey: summaryQueryKey(playthroughId ?? "", summaryId ?? ""),
    queryFn: () => {
      if (!playthroughId || !summaryId) throw new Error("Summary ID is required");
      return getStrategySummary(playthroughId, summaryId);
    },
    enabled: Boolean(playthroughId && summaryId),
  });
}

export function useStrategySummaryStream(playthroughId?: string) {
  const queryClient = useQueryClient();
  const [streaming, setStreaming] = useState<{ summaryId: string; narration: string } | null>(null);
  const [error, setError] = useState<SummaryStreamError | null>(null);
  const invalidate = useCallback((summaryId: string) => {
    if (!playthroughId) return;
    void queryClient.invalidateQueries({ queryKey: getStrategySummariesQueryKey(playthroughId) });
    void queryClient.invalidateQueries({ queryKey: summaryQueryKey(playthroughId, summaryId) });
    void queryClient.invalidateQueries({ queryKey: ["simulation-world", playthroughId] });
  }, [playthroughId, queryClient]);
  const stream = usePostSSE({
    onEvent: (name, data) => {
      if (name === "narration") setStreaming((current) => current && { ...current, narration: current.narration + data });
      if (name === "done") {
        const summaryId = summaryIdFromDone(data);
        if (summaryId) invalidate(summaryId);
        setStreaming(null);
      }
      if (name === "summary_error") setError(parseStreamError(data));
    },
    onError: () => setError({ code: "summary_unavailable", message: "Chronicle could not be loaded. Try again.", is_retryable: true }),
  });
  const start = useCallback((summary: StrategySummaryView) => {
    if (!playthroughId || summary.status === "completed") return;
    setError(null);
    setStreaming({ summaryId: summary.summary_id, narration: "" });
    stream.start(
      getStrategySummaryStreamPath(playthroughId, summary.summary_id),
      { client_request_id: generateClientActionId() },
    );
  }, [playthroughId, stream]);
  const current = useMemo(
    () => streaming ? { ...streaming, isStreaming: stream.status !== "closed" } : null,
    [stream.status, streaming],
  );
  return { ...stream, start, streaming: current, error };
}
