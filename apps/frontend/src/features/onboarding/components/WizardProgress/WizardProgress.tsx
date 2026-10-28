import React from "react";
import {
  INPUT_STEP_IDS,
  INPUT_STEP_LABELS,
} from "../../constants/onboarding.constants";
import type { WizardProgressProps } from "./WizardProgress.types";

export const WizardProgress: React.FC<WizardProgressProps> = ({
  currentStep,
}) => {
  const currentIndex = INPUT_STEP_IDS.indexOf(currentStep);

  return (
    <ol
      aria-label="Setup progress"
      className="mb-8 grid w-full grid-cols-3 gap-3"
    >
      {INPUT_STEP_IDS.map((stepId, index) => {
        const isCompleted = index < currentIndex;
        const isActive = index === currentIndex;

        let barClass = "bg-border-subtle";
        if (isCompleted) {
          barClass = "bg-success";
        } else if (isActive) {
          barClass = "bg-primary";
        }

        return (
          <li
            key={stepId}
            aria-current={isActive ? "step" : undefined}
            className="flex flex-col gap-1.5"
          >
            <div
              className={`h-1 w-full rounded-full transition-all duration-300 ${barClass}`}
            />
            <div className="flex items-center justify-between font-mono text-[11px] text-content-faint">
              <span className={isActive ? "font-medium text-content" : ""}>
                0{index + 1} / {INPUT_STEP_LABELS[stepId]}
              </span>
              {isCompleted && (
                <span className="text-[10px] font-medium text-success">
                  Done
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
};
