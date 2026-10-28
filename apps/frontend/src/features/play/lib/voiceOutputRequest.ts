import { queryClient } from "@/shared/lib/query-client";
import { ALPHA_CONFIG_QUERY_KEY } from "@/shared/hooks/useAlphaConfig";
import { VOICE_OUTPUT_PREFERENCE_QUERY_KEY } from "@/shared/hooks/useVoiceOutputPreference";
import type { AlphaConfig } from "@/shared/types/alpha.types";
import type { VoiceOutputPreference } from "@/shared/types/userPreferences.types";

// Read from React Query's cache directly (imperative, outside a component).
// Defaults to false (safe: matches the opt-in/default-off setting) when the
// preference hasn't loaded yet, and is always false in alpha mode so a
// preference saved before the alpha cannot request paid narration audio.
export function isVoiceOutputRequested(): boolean {
  const alphaConfig = queryClient.getQueryData<AlphaConfig>(
    ALPHA_CONFIG_QUERY_KEY,
  );
  if (alphaConfig?.is_alpha_mode) return false;
  const cached = queryClient.getQueryData<VoiceOutputPreference>(
    VOICE_OUTPUT_PREFERENCE_QUERY_KEY,
  );
  return cached?.voice_output_enabled ?? false;
}
