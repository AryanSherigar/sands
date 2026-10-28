import { SCENARIO_TOOLS, type ToolKey } from "@/shared/constants/scenario-tools";
import type { ConditionResponse } from "../types/condition.types";
import type { MinigameResponse } from "../types/minigame.types";
import type { StateFieldDefinition } from "../types/scenario.types";
import { usesStatusHud } from "./trackedValueEditing";

export interface ToolsInUseInput {
  stateSchema: Record<string, StateFieldDefinition>;
  conditions: ReadonlyArray<Pick<ConditionResponse, "sensory_cue">>;
  sheetRuleCount: number;
  ruleCheckCount: number;
  minigames: ReadonlyArray<Pick<MinigameResponse, "minigame_type">>;
}

const RHYTHM_MINIGAME_TYPE = "rhythm_composure";

const hasStatusHudValue = (schema: Record<string, StateFieldDefinition>): boolean =>
  Object.values(schema).some(
    (field) => usesStatusHud(field) || hasStatusHudValue(field.fields ?? {}),
  );

const addRequirements = (tools: Set<ToolKey>): Set<ToolKey> => {
  SCENARIO_TOOLS.filter((tool) => tools.has(tool.key)).forEach((tool) =>
    tool.requires.forEach((required) => tools.add(required)),
  );
  return tools;
};

export const computeToolsInUse = (input: ToolsInUseInput): Set<ToolKey> => {
  const tools = new Set<ToolKey>();
  if (hasStatusHudValue(input.stateSchema)) tools.add("status_hud");
  if (input.conditions.some((condition) => Boolean(condition.sensory_cue))) {
    tools.add("atmosphere");
  }
  if (input.sheetRuleCount > 0) tools.add("rule_sheet");
  if (input.ruleCheckCount > 0) tools.add("rule_checks");
  if (input.minigames.some((game) => game.minigame_type === RHYTHM_MINIGAME_TYPE)) {
    tools.add("composure");
  }
  return addRequirements(tools);
};
