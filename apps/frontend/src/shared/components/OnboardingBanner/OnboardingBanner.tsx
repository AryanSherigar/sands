import React from "react";
import { Link } from "react-router-dom";
import { useDismissOnboarding } from "@/shared/hooks/useDismissOnboarding";
import { useOnboardingBannerVisibility } from "@/shared/hooks/useOnboardingBannerVisibility";
import { WELCOME_PATH } from "@/shared/lib/onboarding-routes";
import { useOnboardingPromptStore } from "@/shared/stores/onboardingPrompt.store";

export const OnboardingBanner: React.FC = () => {
  const isVisible = useOnboardingBannerVisibility();
  return isVisible ? <OnboardingBannerContent /> : null;
};

const OnboardingBannerContent: React.FC = () => {
  const clearPrompt = useOnboardingPromptStore((state) => state.clearPrompt);
  const dismissal = useDismissOnboarding();

  const handleDismiss = () =>
    dismissal.mutate(undefined, { onSuccess: clearPrompt });

  return (
    <div
      role="region"
      aria-label="Finish setting up"
      className="flex items-center justify-between gap-3 border-b border-border-subtle bg-surface-raised px-4 py-2.5 text-sm text-content"
    >
      <p>Finish setting up — pick your genres (1 min)</p>
      <div className="flex items-center gap-2">
        <Link
          to={WELCOME_PATH}
          className="rounded-md border border-accent bg-accent px-3 py-1 text-xs font-medium text-accent-contrast transition hover:bg-accent-strong focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
        >
          Start
        </Link>
        <button
          type="button"
          aria-label="Dismiss setup reminder"
          disabled={dismissal.isPending}
          onClick={handleDismiss}
          className="rounded-md px-2 py-1 text-content-muted transition hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
        >
          ×
        </button>
      </div>
    </div>
  );
};
