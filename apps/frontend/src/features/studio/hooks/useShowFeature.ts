import { useCallback } from "react";
import { prefersReducedMotion } from "@/shared/lib/prefersReducedMotion";
import type { NewFeature } from "../constants/newFeatures";
import { CHARACTERS_STEP_NUMBER } from "../constants/finish";
import { GUIDE_TAB_ID } from "../constants/studioTabs";
import { buildCardTabId } from "../lib/studioTabs";
import { useNewFeaturesStore } from "../stores/newFeatures.store";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import { useGuideCards } from "./useGuideCards";

export const useShowFeature = () => {
  const { cards } = useGuideCards();
  const openTab = useStudioTabsStore((state) => state.openTab);
  const setGuideStep = useStudioTabsStore((state) => state.setGuideStep);
  const setGuideView = useStudioTabsStore((state) => state.setGuideView);
  const highlightFeature = useNewFeaturesStore((state) => state.highlightFeature);
  const firstCard = cards.characters[0] ?? cards.places[0] ?? cards.groups[0] ?? cards.things[0];

  const openGuideStep = useCallback(
    (stepNumber: number): void => {
      openTab(GUIDE_TAB_ID);
      setGuideView("steps");
      setGuideStep(stepNumber);
    },
    [openTab, setGuideStep, setGuideView],
  );

  return useCallback(
    (feature: NewFeature): void => {
      if (feature.target.kind === "guide-step") openGuideStep(feature.target.stepNumber);
      else if (firstCard) openTab(buildCardTabId(firstCard.entity_id));
      else openGuideStep(CHARACTERS_STEP_NUMBER);
      if (!prefersReducedMotion()) highlightFeature(feature.id);
    },
    [firstCard, highlightFeature, openGuideStep, openTab],
  );
};
