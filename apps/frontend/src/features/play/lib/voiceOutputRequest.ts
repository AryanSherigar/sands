import { queryClient } from "@/shared/lib/query-client";
import { VOICE_OUTPUT_PREFERENCE_QUERY_KEY } from "@/shared/hooks/useVoiceOutputPreference";
import type { VoiceOutputPreference } from "@/shared/types/userPreferences.types";

// Read from React Query's cache directly (imperative, outside a component).
// Defaults to false (safe: matches the opt-in/default-off setting) when the
// preference hasn't loaded yet.
export function isVoiceOutputRequested(): boolean {
  const cached = queryClient.getQueryData<VoiceOutputPreference>(
    VOICE_OUTPUT_PREFERENCE_QUERY_KEY,
  );
  return cached?.voice_output_enabled ?? false;
}
