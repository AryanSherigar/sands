import React, { useId } from "react";
import { ShowExample } from "./ShowExample";
import type { GuideStepLayoutProps } from "./Guide.types";

export const GuideStepLayout: React.FC<GuideStepLayoutProps> = ({
  step,
  children,
  shouldShowExample = true,
}) => {
  const headingId = useId();

  return (
    <section aria-labelledby={headingId} className="space-y-6">
      <header className="space-y-2">
        <h2
          id={headingId}
          className="font-display text-title font-semibold text-content"
        >
          {step.header}
        </h2>
        {step.helper && (
          <p className="text-body text-content-muted">{step.helper}</p>
        )}
      </header>
      {children}
      {shouldShowExample && <ShowExample stepId={step.id} />}
    </section>
  );
};
