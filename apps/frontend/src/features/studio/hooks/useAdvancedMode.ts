import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useMediaQuery } from "@/shared/hooks/useMediaQuery";
import { useToast } from "@/shared/hooks/useToast";
import { logEvent } from "@/shared/lib/logger";
import { updateScenario } from "../api/scenarios.api";
import {
  ADVANCED_MODE_OFF,
  ADVANCED_MODE_ON,
  ADVANCED_SWITCH_FAILED_MESSAGE,
} from "../constants/advancedMode";
import { SCENARIO_QUERY_KEY } from "../constants/studioScenario";
import { ADVANCED_NARROW_MEDIA_QUERY } from "../constants/studioFrame";
import { runGuardedWrite, withEditStamp } from "../lib/editGuard";
import { remapGuideStep } from "../lib/guideStepsFor";
import { useStudioTabsStore } from "../stores/studioTabs.store";
import type { ScenarioMode, ScenarioResponse, ScenarioUpdate } from "../types/scenario.types";
import { useGuide } from "./useGuide";

export interface AdvancedModeControls {
  isAdvanced: boolean;
  canUseAdvanced: boolean;
  isPublishing: boolean;
  isSwitching: boolean;
  turnOn: () => Promise<void>;
  turnOff: () => Promise<void>;
}

export const useAdvancedMode = (): AdvancedModeControls => {
  const { scenario, ensureDraft } = useGuide();
  const queryClient = useQueryClient();
  const showToast = useToast();
  const isNarrow = useMediaQuery(ADVANCED_NARROW_MEDIA_QUERY);
  const isAdvanced = scenario?.mode === ADVANCED_MODE_ON;
  const isPublishing = scenario?.status === "publishing";
  const canUseAdvanced = !isNarrow;

  const switchMutation = useMutation<ScenarioResponse, Error, ScenarioMode>({
    mutationFn: async (mode) => {
      const scenarioId = await ensureDraft();
      const saved = await runGuardedWrite(queryClient, scenarioId, (stamp) =>
        updateScenario(scenarioId, withEditStamp<ScenarioUpdate>({ mode }, stamp)),
      );
      queryClient.setQueryData([SCENARIO_QUERY_KEY, scenarioId], saved);
      return saved;
    },
  });
  const { mutateAsync, isPending } = switchMutation;

  const switchTo = useCallback(
    async (mode: ScenarioMode): Promise<void> => {
      if (isPublishing) return;
      const wasAdvanced = isAdvanced;
      try {
        await mutateAsync(mode);
      } catch (error) {
        logEvent("warning", "advanced_mode_switch_failed", { error: String(error) });
        showToast(ADVANCED_SWITCH_FAILED_MESSAGE, "error");
        return;
      }
      const store = useStudioTabsStore.getState();
      const isNowAdvanced = mode === ADVANCED_MODE_ON;
      store.setGuideStep(remapGuideStep(store.guideStep, wasAdvanced, isNowAdvanced));
      store.setGuideStepMode(isNowAdvanced);
    },
    [isAdvanced, isPublishing, mutateAsync, showToast],
  );

  const turnOn = useCallback(() => switchTo(ADVANCED_MODE_ON), [switchTo]);
  const turnOff = useCallback(() => switchTo(ADVANCED_MODE_OFF), [switchTo]);

  return { isAdvanced, canUseAdvanced, isPublishing, isSwitching: isPending, turnOn, turnOff };
};
