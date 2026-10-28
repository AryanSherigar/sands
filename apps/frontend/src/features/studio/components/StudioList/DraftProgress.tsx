import React from "react";
import { cn } from "@/shared/lib/cn";
import {
  formatDraftProgress,
  getDraftGuideStep,
  readRememberedGuideStep,
} from "../../lib/draftProgress";
import { clampGuideStep, getGuideSteps } from "../../lib/guideStepsFor";
import type { DraftProgressProps } from "./StudioList.types";

export const DraftProgress: React.FC<DraftProgressProps> = ({ scenario }) => {
  const isAdvanced = scenario.mode === "master";
  const steps = getGuideSteps(isAdvanced);
  const stepNumber = clampGuideStep(
    getDraftGuideStep(scenario, readRememberedGuideStep(scenario.scenario_id)),
    isAdvanced,
  );
  const label = formatDraftProgress(stepNumber, isAdvanced);

  return (
    <div className="space-y-1.5">
      <p className="text-meta font-medium text-content">{label}</p>
      <div
        role="progressbar"
        aria-label="Guide progress"
        aria-valuemin={1}
        aria-valuemax={steps.length}
        aria-valuenow={stepNumber}
        aria-valuetext={label}
        className="flex max-w-60 gap-1"
      >
        {steps.map((step) => (
          <span
            key={step.id}
            className={cn(
              "h-1 flex-1 rounded-full",
              step.number <= stepNumber ? "bg-primary" : "bg-border-subtle",
            )}
          />
        ))}
      </div>
    </div>
  );
};
