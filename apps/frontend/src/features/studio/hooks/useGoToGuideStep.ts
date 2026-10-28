import { useCallback } from "react";
import type { GuideStepId } from "../constants/guideSteps";
import { getGuideSteps } from "../lib/guideStepsFor";
import { useStudioTabsStore } from "../stores/studioTabs.store";

export const useGoToGuideStep = (): ((stepId: GuideStepId) => void) => {
  const setGuideStep = useStudioTabsStore((state) => state.setGuideStep);

  return useCallback(
    (stepId: GuideStepId): void => {
      const step = getGuideSteps(true).find((candidate) => candidate.id === stepId);
      if (step) setGuideStep(step.number);
    },
    [setGuideStep],
  );
};
