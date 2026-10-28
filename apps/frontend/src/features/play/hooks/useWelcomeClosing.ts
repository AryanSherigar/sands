import { useMutation } from "@tanstack/react-query";
import { fetchWelcomeClosing } from "../api/voice.api";

export function useWelcomeClosing() {
  return useMutation({
    mutationFn: ({ playthroughId, signal }: { playthroughId: string; signal: AbortSignal }) => fetchWelcomeClosing(playthroughId, signal),
    retry: false,
    gcTime: 0,
  });
}
