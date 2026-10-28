import React from "react";
import { Button } from "@/shared/components/ui/Button";
import {
  ALWAYS_REMEMBER_LINK_LABEL,
  EMPTY_COPY,
  HARD_LIMIT_EXAMPLES,
} from "../../constants/hardLimits";
import { ALWAYS_REMEMBER_SECTION_ID } from "../../constants/advancedCards";
import { useGoToGuideStep } from "../../hooks/useGoToGuideStep";
import { useHardLimitCommands } from "../../hooks/useHardLimitCommands";
import { useValueOptions } from "../../hooks/useValueOptions";
import { getGuideStep } from "../../lib/guideSteps";
import { ExampleChips } from "./advanced/ExampleChips";
import { HardLimitCard } from "./advanced/HardLimitCard";
import { GuideStepLayout } from "./GuideStepLayout";

const EXAMPLE_CHIPS = HARD_LIMIT_EXAMPLES.map(({ id, label }) => ({ id, label }));

export const StepHardLimits: React.FC = () => {
  const options = useValueOptions();
  const commands = useHardLimitCommands(options);
  const goToStep = useGoToGuideStep();

  const handleOpenAlwaysRemember = (): void => {
    goToStep("world");
    window.requestAnimationFrame(() =>
      document.getElementById(ALWAYS_REMEMBER_SECTION_ID)?.scrollIntoView?.({ block: "start" }),
    );
  };

  return (
    <GuideStepLayout step={getGuideStep("hard_limits")}>
      {commands.limits.length === 0 && !commands.isLoading && (
        <p className="text-meta text-content-muted">{EMPTY_COPY}</p>
      )}
      <div className="space-y-4">
        {commands.limits.map((limit, index) => (
          <HardLimitCard
            key={limit.invariant_id}
            limit={limit}
            index={index}
            onUpdate={(patch) => commands.updateLimit(limit.invariant_id, patch)}
            onDuplicate={() => commands.duplicateLimit(limit)}
            onDelete={() => commands.deleteLimit(limit.invariant_id)}
          />
        ))}
      </div>
      <Button type="button" variant="secondary" onClick={commands.addLimit}>
        + Add a hard limit
      </Button>
      <ExampleChips heading="Examples" examples={EXAMPLE_CHIPS} onPick={commands.addExample} />
      <button
        type="button"
        onClick={handleOpenAlwaysRemember}
        className="text-meta font-medium text-content-muted underline underline-offset-4 transition-colors hover:text-content"
      >
        {ALWAYS_REMEMBER_LINK_LABEL}
      </button>
    </GuideStepLayout>
  );
};
