import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSSE } from "@/shared/hooks/useSSE";

import { ScenarioMood } from "@/shared/types/audio.types";
import { ambientSoundtrack } from "@/shared/lib/audio/ambient-soundtrack";
import { getMoodTrackUrl } from "@/shared/constants/audio";

const TRS_BASE_URL = import.meta.env.VITE_TRS_URL || "http://localhost:8001";


/** Read-only live narration stream for spectators, gated on a share token. */
export function useSpectator(
  playthroughId: string | null,
  shareToken: string | null,
  musicTracks?: Partial<Record<ScenarioMood, string | null>>,
) {
  const [streamingText, setStreamingText] = useState("");
  const [streamingImageUrl, setStreamingImageUrl] = useState<string | null>(
    null,
  );
  const [isLive, setIsLive] = useState(false);
  const [degradedMessage, setDegradedMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const invalidatePlaythroughQueries = useCallback(async () => {
    if (!playthroughId) return;
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["playthrough-turns", playthroughId],
      }),
      queryClient.invalidateQueries({
        queryKey: ["playthrough", playthroughId],
      }),
    ]);
  }, [playthroughId, queryClient]);

  const handleEvent = useCallback(
    async (eventName: string, data: string) => {
      if (eventName === "mood") {
        const mood = data as ScenarioMood;
        ambientSoundtrack.transitionTo(
          mood,
          getMoodTrackUrl(mood, musicTracks),
        );
      } else if (eventName === "narration") {
        setIsLive(true);
        setStreamingText((prev) => prev + data);
      } else if (eventName === "scene_image") {
        setStreamingImageUrl(data);
      } else if (eventName === "degraded") {
        setIsLive(false);
        setStreamingText("");
        setStreamingImageUrl(null);
        setDegradedMessage(
          data || "The narrator connection was interrupted.",
        );
      } else if (eventName === "done") {
        setIsLive(false);
        await invalidatePlaythroughQueries();
        setStreamingText("");
        setStreamingImageUrl(null);
      }
    },
    [invalidatePlaythroughQueries, musicTracks],
  );

  const url =
    playthroughId && shareToken
      ? `${TRS_BASE_URL}/v1/session/${playthroughId}/spectate?share_token=${encodeURIComponent(shareToken)}`
      : null;

  const status = useSSE(url, handleEvent, Boolean(url));

  const clearDegradedMessage = useCallback(() => setDegradedMessage(null), []);

  return {
    streamingText,
    streamingImageUrl,
    isLive,
    status,
    degradedMessage,
    clearDegradedMessage,
  };
}
