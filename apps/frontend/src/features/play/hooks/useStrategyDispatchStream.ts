import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getStrategyDispatchStreamPath } from "../api/simulation.api";
import { getStrategyDispatchesQueryKey } from "./useStrategyDispatches";
import type { StrategyDispatchView } from "../types/simulation.types";
import { generateClientActionId } from "@/shared/lib/request-id";
import { usePostSSE } from "@/shared/hooks/usePostSSE";

interface StreamingDispatch {
  rumorId: string;
  narration: string;
}

export function useStrategyDispatchStream(playthroughId?: string) {
  const queryClient = useQueryClient();
  const [streaming, setStreaming] = useState<StreamingDispatch | null>(null);
  const [degradedRumorIds, setDegradedRumorIds] = useState<string[]>([]);
  const activeRumorIdRef = useRef<string | null>(null);

  const refreshList = useCallback(() => {
    void queryClient.invalidateQueries({
      queryKey: getStrategyDispatchesQueryKey(playthroughId),
    });
  }, [playthroughId, queryClient]);

  const markDegraded = useCallback(() => {
    const rumorId = activeRumorIdRef.current;
    activeRumorIdRef.current = null;
    setStreaming(null);
    if (rumorId) {
      setDegradedRumorIds((ids) => (ids.includes(rumorId) ? ids : [...ids, rumorId]));
    }
    refreshList();
  }, [refreshList]);

  const stream = usePostSSE({
    onEvent: (name, data) => {
      if (name === "narration") {
        setStreaming((current) => current && { ...current, narration: current.narration + data });
      }
      if (name === "done") {
        activeRumorIdRef.current = null;
        setStreaming(null);
        refreshList();
      }
      if (name === "degraded") markDegraded();
    },
    onError: markDegraded,
  });

  const start = useCallback(
    (dispatch: StrategyDispatchView) => {
      if (!playthroughId || dispatch.status === "completed") return;
      setDegradedRumorIds((ids) => ids.filter((id) => id !== dispatch.rumor_id));
      activeRumorIdRef.current = dispatch.rumor_id;
      setStreaming({ rumorId: dispatch.rumor_id, narration: "" });
      stream.start(getStrategyDispatchStreamPath(playthroughId, dispatch.rumor_id), {
        client_request_id: generateClientActionId(),
      });
    },
    [playthroughId, stream],
  );

  return { streaming, degradedRumorIds, start };
}
