import React from "react";
import { Button } from "@/shared/components/ui/Button";
import { RULE_EXAMPLES } from "../../constants/rules";
import { useRuleCommands } from "../../hooks/useRuleCommands";
import { useTurnOffUnusedTool } from "../../hooks/useTurnOffUnusedTool";
import { useValueOptions } from "../../hooks/useValueOptions";
import { getGuideStep } from "../../lib/guideSteps";
import { ExampleChips } from "./advanced/ExampleChips";
import { RuleCard } from "./advanced/RuleCard";
import { TurnOffToolPrompt } from "./advanced/TurnOffToolPrompt";
import { GuideStepLayout } from "./GuideStepLayout";

const EMPTY_COPY = "No rules yet. Add one, or tap an example below to start from.";
const EXAMPLE_CHIPS = RULE_EXAMPLES.map(({ id, label }) => ({ id, label }));

export const StepRules: React.FC = () => {
  const options = useValueOptions();
  const commands = useRuleCommands(options);
  const atmosphereTool = useTurnOffUnusedTool("atmosphere");

  const handleDelete = (conditionId: string, hasSound: boolean): void => {
    commands.deleteRule(conditionId);
    if (hasSound) atmosphereTool.askAfterRemoval();
  };

  return (
    <GuideStepLayout step={getGuideStep("rules")}>
      {commands.rules.length === 0 && !commands.isLoading && (
        <p className="text-meta text-content-muted">{EMPTY_COPY}</p>
      )}
      <div className="space-y-4">
        {commands.rules.map((rule, index) => (
          <RuleCard
            key={rule.condition_id}
            rule={rule}
            index={index}
            onUpdate={(patch) => commands.updateRule(rule.condition_id, patch)}
            onDuplicate={() => commands.duplicateRule(rule)}
            onDelete={() => handleDelete(rule.condition_id, Boolean(rule.sensory_cue))}
            onSoundRemoved={atmosphereTool.askAfterRemoval}
          />
        ))}
      </div>
      <TurnOffToolPrompt tool={atmosphereTool} />
      <Button type="button" variant="secondary" onClick={commands.addRule}>
        + Add a rule
      </Button>
      <ExampleChips heading="Questions to help" examples={EXAMPLE_CHIPS} onPick={commands.addExample} />
    </GuideStepLayout>
  );
};
