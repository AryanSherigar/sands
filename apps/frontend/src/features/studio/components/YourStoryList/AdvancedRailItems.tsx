import React from "react";
import { IconCircle } from "@tabler/icons-react";
import { SidebarButton } from "@/shared/components/layout/SidebarButton";
import { ADVANCED_RAIL_LABEL } from "../../constants/advancedMode";
import { ADVANCED_GUIDE_STEPS } from "../../constants/advancedSteps";
import type { GuideStepId } from "../../constants/guideSteps";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { useConditions } from "../../hooks/useConditions";
import { useEndConditions } from "../../hooks/useEndConditions";
import { useGuide } from "../../hooks/useGuide";
import { useInvariants } from "../../hooks/useInvariants";
import { getGuideSteps } from "../../lib/guideStepsFor";
import { listTrackedValueOptions } from "../../lib/valueOptions";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { YourStoryGroup } from "./YourStoryGroup";
import type { AdvancedRailItemsProps } from "./YourStoryList.types";

export const AdvancedRailItems: React.FC<AdvancedRailItemsProps> = ({ filterText }) => {
  const { scenarioId, scenario } = useGuide();
  const { endConditions } = useEndConditions(scenarioId);
  const { conditions } = useConditions(scenarioId);
  const { invariants } = useInvariants(scenarioId);
  const guideStep = useStudioTabsStore((state) => state.guideStep);
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const needle = filterText.trim().toLowerCase();
  const visibleSteps = ADVANCED_GUIDE_STEPS.filter((step) =>
    step.name.toLowerCase().includes(needle),
  );
  if (needle && visibleSteps.length === 0) return null;

  const counts: Partial<Record<GuideStepId, number>> = {
    endings: endConditions.length,
    tracked_values: listTrackedValueOptions(scenario?.state_schema ?? {}).length,
    rules: conditions.length,
    hard_limits: invariants.length,
  };
  const total = Object.values(counts).reduce<number>((sum, count) => sum + (count ?? 0), 0);
  const formatCount = (stepId: GuideStepId): string | undefined => {
    const count = counts[stepId];
    return count === undefined ? undefined : String(count);
  };
  const numberOf = (stepId: GuideStepId): number =>
    getGuideSteps(true).find((step) => step.id === stepId)?.number ?? 1;

  const handleOpenStep = (stepId: GuideStepId): void => {
    const store = useStudioTabsStore.getState();
    store.openTab(GUIDE_TAB_ID);
    store.focusTab(GUIDE_TAB_ID);
    store.setGuideStep(numberOf(stepId));
    store.setGuideView("steps");
  };

  return (
    <YourStoryGroup label={ADVANCED_RAIL_LABEL} count={total}>
      {visibleSteps.map((step) => (
        <SidebarButton
          key={step.id}
          icon={<IconCircle size={14} aria-hidden="true" />}
          label={step.name}
          trailing={formatCount(step.id)}
          isActive={activeTabId === GUIDE_TAB_ID && guideStep === numberOf(step.id)}
          onClick={() => handleOpenStep(step.id)}
        />
      ))}
    </YourStoryGroup>
  );
};
