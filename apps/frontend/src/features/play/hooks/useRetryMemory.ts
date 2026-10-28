import { useMutation } from "@tanstack/react-query";
import { retryMemory } from "../api/memory.api";
import { usePlayStore } from "../stores/play.store";

export const useRetryMemory = (playthroughId: string) => {
  const setMemoryDegradedReasons = usePlayStore(
    (s) => s.setMemoryDegradedReasons,
  );
  return useMutation({
    mutationFn: () => retryMemory(playthroughId),
    onSuccess: (response) => setMemoryDegradedReasons(response.degraded_reasons),
  });
};
