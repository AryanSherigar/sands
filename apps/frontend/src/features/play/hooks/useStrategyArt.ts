import { isAxiosError } from "axios";
import { useQuery } from "@tanstack/react-query";
import { requestStrategyArt } from "../api/strategyArt.api";
import type { StrategyArtKind } from "../types/strategyArt.types";

export const ART_POLL_INTERVAL_MS = 3000;
const HTTP_CONFLICT = 409;
const HTTP_NOT_FOUND = 404;

const strategyArtQueryKey = (
  playthroughId: string | undefined,
  kind: StrategyArtKind,
  itemId: string | undefined,
) => ["strategy-art", playthroughId, kind, itemId] as const;

function isInProgressError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === HTTP_CONFLICT;
}

function isItemGoneError(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === HTTP_NOT_FOUND;
}

export interface StrategyArtState {
  artUrl: string | null;
  isLoading: boolean;
  hasFailed: boolean;
  canRetry: boolean;
  retry: () => void;
}

function isStillPainting(status: string | undefined): boolean {
  return status === "pending" || status === "generating";
}

export function useStrategyArt(
  playthroughId: string | undefined,
  kind: StrategyArtKind,
  itemId: string | undefined,
  pollIntervalMs: number = ART_POLL_INTERVAL_MS,
): StrategyArtState {
  const isEnabled = Boolean(playthroughId && itemId);
  const query = useQuery({
    queryKey: strategyArtQueryKey(playthroughId, kind, itemId),
    queryFn: () => requestStrategyArt(playthroughId ?? "", kind, itemId ?? ""),
    enabled: isEnabled,
    staleTime: Infinity,
    retry: false,
    refetchInterval: (current) =>
      isInProgressError(current.state.error) || isStillPainting(current.state.data?.status)
        ? pollIntervalMs
        : false,
  });
  const isCompleted = query.data?.status === "completed";
  const isGenerationFailed = query.data?.status === "failed";
  const isRequestFailed = query.isError && !isInProgressError(query.error);
  const hasFailed = isEnabled && (isGenerationFailed || isRequestFailed);
  return {
    artUrl: isCompleted ? (query.data?.art_url ?? null) : null,
    isLoading:
      isEnabled &&
      !hasFailed &&
      (query.isPending || isInProgressError(query.error) || isStillPainting(query.data?.status)),
    hasFailed,
    canRetry: !isItemGoneError(query.error) && (!isGenerationFailed || Boolean(query.data?.is_retryable)),
    retry: () => void query.refetch(),
  };
}
