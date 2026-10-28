import { useAuthStore } from "@/features/auth/stores/auth.store";

export const useOnboardingBannerVisibility = (): boolean =>
  useAuthStore((state) => state.user?.onboarding_completed === false);
