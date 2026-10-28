import React from "react";
import { IconCheck, IconCircle, IconCircleFilled } from "@tabler/icons-react";
import { SidebarButton } from "@/shared/components/layout/SidebarButton";
import { GUIDE_TAB_ID } from "../../constants/studioTabs";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { getStepStatus, isStepDone, type GuideStepStatus } from "../../lib/guideProgress";
import { getGuideSteps, isAdvancedStepId } from "../../lib/guideStepsFor";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { YourStoryGroup } from "./YourStoryGroup";
import type { GuideStepItemsProps, StatusIconProps } from "./YourStoryList.types";

const STATUS_TEXT: Record<GuideStepStatus, string> = {
  done: "Done",
  current: "In progress",
  todo: "Not started",
};

const StatusIcon: React.FC<StatusIconProps> = ({ status }) => (
  <>
    {status === "done" && <IconCheck size={16} aria-hidden="true" />}
    {status === "current" && <IconCircleFilled size={10} aria-hidden="true" />}
    {status === "todo" && <IconCircle size={14} aria-hidden="true" />}
    <span className="sr-only">{STATUS_TEXT[status]}</span>
  </>
);

export const GuideStepItems: React.FC<GuideStepItemsProps> = ({ filterText }) => {
  const { scenario } = useGuide();
  const { cards } = useGuideCards();
  const guideStep = useStudioTabsStore((state) => state.guideStep);
  const activeTabId = useStudioTabsStore((state) => state.activeTabId);
  const needle = filterText.trim().toLowerCase();
  const steps = getGuideSteps(scenario?.mode === "master").filter((step) => !isAdvancedStepId(step.id));
  const visibleSteps = steps.filter((step) => step.name.toLowerCase().includes(needle));
  if (needle && visibleSteps.length === 0) return null;

  const handleOpenStep = (stepNumber: number): void => {
    const store = useStudioTabsStore.getState();
    store.openTab(GUIDE_TAB_ID);
    store.focusTab(GUIDE_TAB_ID);
    store.setGuideStep(stepNumber);
    store.setGuideView("steps");
  };

  return (
    <YourStoryGroup label="Guide" count={steps.length}>
      {visibleSteps.map((step) => {
        const status = getStepStatus(step.number, guideStep, isStepDone(step.id, scenario, cards));
        return (
          <SidebarButton
            key={step.id}
            icon={<StatusIcon status={status} />}
            label={`${step.number}. ${step.name}`}
            isActive={activeTabId === GUIDE_TAB_ID && guideStep === step.number}
            onClick={() => handleOpenStep(step.number)}
          />
        );
      })}
    </YourStoryGroup>
  );
};
