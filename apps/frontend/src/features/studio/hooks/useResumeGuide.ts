import { useEffect } from "react";
import { getFirstUnfinishedStep } from "../lib/guideProgress";
import { getGuideStepName } from "../lib/guideSteps";
import { useStudioStore } from "../stores/studio.store";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { useGuide } from "./useGuide";
import { useGuideCards } from "./useGuideCards";

const hasStoryContent = (title: string, logline: string | null): boolean =>
  Boolean(title.trim() || logline?.trim());

export const useResumeGuide = (): void => {
  const { scenario } = useGuide();
  const { cards, isLoading } = useGuideCards();
  const isResumePending = useStudioTabsStore((state) => state.isResumePending);
  const completeResume = useStudioTabsStore((state) => state.completeResume);
  const clearWelcomeBack = useStudioTabsStore((state) => state.clearWelcomeBack);
  const isSaving = useStudioStore((state) => state.isSaving);

  useEffect(() => {
    if (!isResumePending || !scenario || isLoading) return;
    const isReturning =
      scenario.status !== "published" && hasStoryContent(scenario.title, scenario.logline);
    if (!isReturning) {
      completeResume(null, null);
      return;
    }
    const isAdvanced = scenario.mode === "master";
    const stepNumber = getFirstUnfinishedStep(scenario, cards, isAdvanced);
    completeResume(stepNumber, getGuideStepName(stepNumber, isAdvanced));
  }, [cards, completeResume, isLoading, isResumePending, scenario]);

  useEffect(() => {
    if (isSaving) clearWelcomeBack();
  }, [clearWelcomeBack, isSaving]);
};
