import { useEffect } from "react";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import type { ScenarioResponse } from "../types/scenario.types";

export const useReconcileGuideStep = (scenario: ScenarioResponse | null): void => {
  const savedMode = useStudioTabsStore((state) => state.isGuideStepAdvanced);
  const reconcileGuideStep = useStudioTabsStore((state) => state.reconcileGuideStep);
  const isAdvanced = scenario ? scenario.mode === "master" : null;

  useEffect(() => {
    if (isAdvanced !== null && savedMode !== isAdvanced) reconcileGuideStep(isAdvanced);
  }, [isAdvanced, reconcileGuideStep, savedMode]);
};
