import type { OnboardingPayload } from "@/shared/types/onboarding.types";
import type { OnboardingDraft } from "../types/onboarding.types";

export function buildOnboardingPayload(draft: OnboardingDraft): OnboardingPayload {
  const displayName = draft.displayName.trim();
  const bio = draft.bio.trim();
  return {
    preferred_genres: draft.genres,
    ...(displayName && { display_name: displayName }),
    ...(bio && { bio }),
    ...(draft.avatarUrl && { avatar_url: draft.avatarUrl }),
    ...(draft.bannerUrl && { banner_url: draft.bannerUrl }),
  };
}
