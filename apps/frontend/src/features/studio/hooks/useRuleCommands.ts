import { useCallback } from "react";
import { buildRuleCopy, buildNewRule } from "../lib/ruleDraft";
import { buildRuleFromExample } from "../lib/ruleExamples";
import { RULE_EXAMPLES } from "../constants/rules";
import type { ConditionResponse, ConditionUpdate } from "../types/condition.types";
import type { ValueOption } from "../types/sentence.types";
import { useConditions } from "./useConditions";
import { useGuide } from "./useGuide";

interface RuleCommands {
  rules: ConditionResponse[];
  isLoading: boolean;
  addRule: () => void;
  duplicateRule: (row: ConditionResponse) => void;
  addExample: (exampleId: string) => void;
  updateRule: (conditionId: string, payload: ConditionUpdate) => void;
  deleteRule: (conditionId: string) => void;
}

export const useRuleCommands = (options: readonly ValueOption[]): RuleCommands => {
  const { scenarioId } = useGuide();
  const rules = useConditions(scenarioId);
  const { createCondition, updateCondition, deleteCondition } = rules;

  const addRule = useCallback((): void => createCondition(buildNewRule()), [createCondition]);
  const duplicateRule = useCallback(
    (row: ConditionResponse): void => createCondition(buildRuleCopy(row)),
    [createCondition],
  );
  const addExample = useCallback(
    (exampleId: string): void => {
      const example = RULE_EXAMPLES.find((candidate) => candidate.id === exampleId);
      if (example) createCondition(buildRuleFromExample(example, options));
    },
    [createCondition, options],
  );
  const updateRule = useCallback(
    (conditionId: string, payload: ConditionUpdate): void => updateCondition({ conditionId, payload }),
    [updateCondition],
  );

  return {
    rules: rules.conditions,
    isLoading: rules.isLoading,
    addRule,
    duplicateRule,
    addExample,
    updateRule,
    deleteRule: deleteCondition,
  };
};
