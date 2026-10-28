import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { useGuide } from "../../hooks/useGuide";
import { useGuideCards } from "../../hooks/useGuideCards";
import { getFirstUnfinishedStep } from "../../lib/guideProgress";
import { getGuideSteps } from "../../lib/guideStepsFor";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { GUIDE_STEP_COMPONENTS } from "./guideStepComponents";

export const GuideEditorView: React.FC = () => {
  const { scenario } = useGuide();
  const { cards } = useGuideCards();
  const isAdvanced = scenario?.mode === "master";
  const setGuideStep = useStudioTabsStore((state) => state.setGuideStep);
  const setGuideView = useStudioTabsStore((state) => state.setGuideView);

  const handleOpenGuide = (): void => {
    setGuideStep(getFirstUnfinishedStep(scenario, cards, isAdvanced));
    setGuideView("steps");
  };

  return (
    <div className="space-y-16">
      <div className="flex justify-end">
        <Button type="button" variant="secondary" size="sm" onClick={handleOpenGuide}>
          Open Guide
        </Button>
      </div>
      {getGuideSteps(isAdvanced).map((step) => {
        const StepComponent = GUIDE_STEP_COMPONENTS[step.id];
        return <StepComponent key={step.id} />;
      })}
    </div>
  );
};
