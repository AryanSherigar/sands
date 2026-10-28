import { useEffect } from "react";
import { fetchOnboardingProfileDraft } from "@/shared/api/onboarding.api";
import { logEvent } from "@/shared/lib/logger";
import { useOnboardingStore } from "../stores/onboarding.store";

export const useRedoPrefill = (isRedo: boolean): void => {
  const hydrate = useOnboardingStore((state) => state.hydrate);
  const goToStep = useOnboardingStore((state) => state.goToStep);

  useEffect(() => {
    if (!isRedo) return;
    fetchOnboardingProfileDraft()
      .then((profile) => {
        hydrate({
          genres: profile.preferred_genres,
          displayName: profile.display_name,
          bio: profile.bio ?? "",
          avatarUrl: profile.avatar_url,
          bannerUrl: profile.banner_url,
        });
      })
      .catch((error: unknown) =>
        logEvent("warning", "onboarding_redo_prefill_failed", { error: String(error) }),
      )
      .finally(() => goToStep("genres"));
  }, [isRedo, hydrate, goToStep]);
};
