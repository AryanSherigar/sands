import React from "react";
import { IconArrowLeft } from "@tabler/icons-react";
import type { StepBarProps } from "./Guide.types";

const BAR_BUTTON_CLASSES =
  "text-meta text-content-muted transition-colors hover:text-content focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-primary";

export const StepBar: React.FC<StepBarProps> = ({ step, stepCount, onBack, onSkipToEditor }) => (
  <nav
    aria-label="Guide steps"
    className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-border-subtle pb-3 text-meta"
  >
    {step.number > 1 && (
      <button type="button" onClick={onBack} className={`${BAR_BUTTON_CLASSES} inline-flex items-center gap-1`}>
        <IconArrowLeft size={14} aria-hidden="true" />
        Back
      </button>
    )}
    <span className="text-content">
      Step {step.number} of {stepCount}
    </span>
    <span className="text-content-muted">{step.name}</span>
    <button
      type="button"
      onClick={onSkipToEditor}
      className={`${BAR_BUTTON_CLASSES} ml-auto underline underline-offset-4`}
    >
      Skip to full editor
    </button>
  </nav>
);
