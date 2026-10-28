import React, { useEffect, useState } from "react";
import { Button } from "@/shared/components/ui/Button";
import { useAdvancedMode } from "../../hooks/useAdvancedMode";
import { clampGuideStep, getGuideSteps } from "../../lib/guideStepsFor";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { GUIDE_STEP_COMPONENTS } from "./guideStepComponents";
import { AdvancedInvitation } from "./AdvancedInvitation";
import { StepBar } from "./StepBar";

export const GuideStepView: React.FC = () => {
  const { isAdvanced, canUseAdvanced, isPublishing, isSwitching, turnOn } = useAdvancedMode();
  const guideStep = useStudioTabsStore((state) => state.guideStep);
  const setGuideStep = useStudioTabsStore((state) => state.setGuideStep);
  const setGuideView = useStudioTabsStore((state) => state.setGuideView);
  const welcomeBackStepName = useStudioTabsStore((state) => state.welcomeBackStepName);
  const steps = getGuideSteps(isAdvanced);
  const stepCount = steps.length;
  const clampStep = (stepNumber: number): number =>
    Math.min(stepCount, Math.max(1, stepNumber));
  const step = steps[clampGuideStep(guideStep, isAdvanced) - 1];
  const StepComponent = GUIDE_STEP_COMPONENTS[step.id];
  const [invitingStepNumber, setInvitingStepNumber] = useState<number | null>(null);
  const isInviting = invitingStepNumber === step.number && !isAdvanced;

  useEffect(() => {
    if (invitingStepNumber === null || !isAdvanced) return;
    setInvitingStepNumber(null);
    if (guideStep === invitingStepNumber) setGuideStep(invitingStepNumber + 1);
  }, [guideStep, invitingStepNumber, isAdvanced, setGuideStep]);

  const handleNext = (): void => {
    if (step.id === "opening" && !isAdvanced) setInvitingStepNumber(step.number);
    else setGuideStep(clampStep(step.number + 1));
  };
  const handleDecline = (): void => {
    setInvitingStepNumber(null);
    setGuideStep(clampStep(step.number + 1));
  };

  return (
    <div className="space-y-8">
      {welcomeBackStepName && (
        <p role="status" className="text-meta text-content-muted">
          Welcome back. You were working on {welcomeBackStepName}.
        </p>
      )}
      <StepBar
        step={step}
        stepCount={stepCount}
        onBack={() => setGuideStep(clampStep(step.number - 1))}
        onSkipToEditor={() => setGuideView("editor")}
      />
      <StepComponent />
      {isInviting && (
        <AdvancedInvitation
          canUseAdvanced={canUseAdvanced}
          isPublishing={isPublishing}
          isBusy={isSwitching}
          onAccept={() => void turnOn()}
          onDecline={handleDecline}
        />
      )}
      {!isInviting && step.number < stepCount && (
        <div className="flex justify-end border-t border-border-subtle pt-6">
          <Button type="button" onClick={handleNext}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
};
