import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchVoiceOutputPreference,
  updateVoiceOutputPreference,
} from "../api/userPreferences.api";

export const VOICE_OUTPUT_PREFERENCE_QUERY_KEY = ["voice-output-preference"];

/** Opt-in, default-off per-player TTS setting (feature/play's header toggle
 * and per-turn play button both gate on this). Server state via React
 * Query, not Zustand, since it must persist across sessions/devices. */
export function useVoiceOutputPreference() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: VOICE_OUTPUT_PREFERENCE_QUERY_KEY,
    queryFn: fetchVoiceOutputPreference,
    staleTime: 1000 * 60 * 5,
  });

  const mutation = useMutation({
    mutationFn: updateVoiceOutputPreference,
    onSuccess: (data) => {
      queryClient.setQueryData(VOICE_OUTPUT_PREFERENCE_QUERY_KEY, data);
    },
  });

  return {
    isVoiceOutputEnabled: query.data?.voice_output_enabled ?? false,
    isLoading: query.isLoading,
    setVoiceOutputEnabled: (enabled: boolean) => mutation.mutate(enabled),
    isUpdating: mutation.isPending,
  };
}
