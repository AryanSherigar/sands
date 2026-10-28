import { useMemo } from "react";
import type { ToolKey } from "@/shared/constants/scenario-tools";
import { computeToolsInUse, type ToolsInUseInput } from "../lib/toolsInUse";
import { useConditions } from "./useConditions";
import { useGuide } from "./useGuide";
import { useMinigames } from "./useMinigames";
import { useRuleChecks } from "./useRuleChecks";
import { useSheetRules } from "./useSheetRules";

export const useToolsInUse = (): {
  toolsInUse: Set<ToolKey>;
  usage: ToolsInUseInput;
  isReady: boolean;
} => {
  const { scenarioId, scenario } = useGuide();
  const { conditions, isLoading: isLoadingConditions } = useConditions(scenarioId);
  const { rules, isLoading: isLoadingSheet } = useSheetRules(scenarioId);
  const { checks, isLoading: isLoadingChecks } = useRuleChecks(scenarioId);
  const { minigames, isLoading: isLoadingMinigames } = useMinigames(scenarioId);
  const stateSchema = scenario?.state_schema;

  const usage = useMemo<ToolsInUseInput>(
    () => ({
      stateSchema: stateSchema ?? {},
      conditions,
      sheetRuleCount: rules.length,
      ruleCheckCount: checks.length,
      minigames,
    }),
    [checks.length, conditions, minigames, rules.length, stateSchema],
  );
  const toolsInUse = useMemo(() => computeToolsInUse(usage), [usage]);
  const isReady =
    Boolean(scenario) &&
    !isLoadingConditions &&
    !isLoadingSheet &&
    !isLoadingChecks &&
    !isLoadingMinigames;

  return { toolsInUse, usage, isReady };
};
