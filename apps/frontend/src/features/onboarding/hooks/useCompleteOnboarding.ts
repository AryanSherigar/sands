import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { useReaderPreferencesStore } from "@/shared/stores/readerPreferences.store";
import { completeOnboarding, redoOnboarding } from "@/shared/api/onboarding.api";
import type { OnboardingResult } from "@/shared/types/onboarding.types";
import { useOnboardingStore } from "../stores/onboarding.store";
import { buildOnboardingPayload } from "../utils/buildOnboardingPayload";

function applyReaderPreferences(): void {
  const draft = useOnboardingStore.getState();
  const reader = useReaderPreferencesStore.getState();
  reader.setTheme(draft.readerTheme);
  reader.setFontSize(draft.readerFontSize);
  reader.setFontId(draft.readerFontId);
  reader.setLineHeight(draft.readerLineHeight);
}

export const useCompleteOnboarding = (isRedo = false) => {
  const queryClient = useQueryClient();

  return useMutation<OnboardingResult, Error, void>({
    mutationFn: () => {
      const payload = buildOnboardingPayload(useOnboardingStore.getState());
      return isRedo ? redoOnboarding(payload) : completeOnboarding(payload);
    },
    onSuccess: (result) => {
      applyReaderPreferences();
      useAuthStore.getState().patchUser({
        display_name: result.display_name,
        onboarding_completed: true,
      });
      queryClient.invalidateQueries({ queryKey: ["user-profile"] });
    },
  });
};
