import React from "react";
import { useExtras } from "../../hooks/useExtras";
import { getGuideStep } from "../../lib/guideSteps";
import { ExtraCard } from "./advanced/ExtraCard";
import { GuideStepLayout } from "./GuideStepLayout";

export const StepExtras: React.FC = () => {
  const { views, add, open, remove } = useExtras();

  return (
    <GuideStepLayout step={getGuideStep("extras")}>
      <div className="grid gap-4 sm:grid-cols-2">
        {views.map(({ extra, isOn, removal }) => (
          <ExtraCard
            key={extra.id}
            extra={extra}
            isOn={isOn}
            removal={removal}
            onAdd={() => void add(extra)}
            onEdit={() => open(extra)}
            onRemove={() => void remove(extra)}
          />
        ))}
      </div>
    </GuideStepLayout>
  );
};
