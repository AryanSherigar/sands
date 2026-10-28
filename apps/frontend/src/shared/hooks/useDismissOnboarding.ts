import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/features/auth/stores/auth.store";
import { completeOnboarding } from "@/shared/api/onboarding.api";
import type { OnboardingResult } from "@/shared/types/onboarding.types";

export const useDismissOnboarding = () => {
  const queryClient = useQueryClient();

  return useMutation<OnboardingResult, Error, void>({
    mutationFn: () => completeOnboarding({ preferred_genres: [] }),
    onSuccess: () => {
      useAuthStore.getState().patchUser({ onboarding_completed: true });
      queryClient.invalidateQueries({ queryKey: ["user-profile"] });
    },
  });
};
