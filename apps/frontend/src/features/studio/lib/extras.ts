import { SCENARIO_TOOLS } from "@/shared/constants/scenario-tools";
import {
  EXTRAS,
  EXTRA_TAB_PREFIX,
  type ExtraDefinition,
  type ExtraId,
  type ExtraRemoval,
} from "../constants/extras";
import { buildFeatureTabId } from "./studioTabs";
import { computeToolsInUse, type ToolsInUseInput } from "./toolsInUse";

const OWN_CONTENT: Partial<Record<ExtraId, Partial<ToolsInUseInput>>> = {
  rule_sheet: { sheetRuleCount: 0 },
  rule_checks: { ruleCheckCount: 0 },
};

export interface ExtraStateInput {
  isAdvanced: boolean;
  enabledTools: readonly string[];
  hasContent: boolean;
}

export const isExtraOn = (extra: ExtraDefinition, input: ExtraStateInput): boolean => {
  if (!input.isAdvanced) return false;
  if (extra.tool) return input.enabledTools.includes(extra.tool);
  return input.hasContent;
};

export const buildExtraTabId = (extraId: ExtraId): string =>
  buildFeatureTabId(`${EXTRA_TAB_PREFIX}${extraId}`);

export const getExtraByFeatureId = (featureId: string): ExtraDefinition | null => {
  if (!featureId.startsWith(EXTRA_TAB_PREFIX)) return null;
  const extraId = featureId.slice(EXTRA_TAB_PREFIX.length);
  return EXTRAS.find((extra) => extra.id === extraId) ?? null;
};

export const hasToolUseOutsideExtra = (extra: ExtraDefinition, usage: ToolsInUseInput): boolean => {
  if (!extra.tool) return false;
  return computeToolsInUse({ ...usage, ...OWN_CONTENT[extra.id] }).has(extra.tool);
};

export const buildExtraRemoval = (
  extra: ExtraDefinition,
  usage: ToolsInUseInput,
  isReady: boolean,
): ExtraRemoval | null => {
  if (!extra.tool) return null;
  const toolName = SCENARIO_TOOLS.find((tool) => tool.key === extra.tool)?.displayName ?? extra.name;
  if (!isReady) return { toolName, state: "checking" };
  return { toolName, state: hasToolUseOutsideExtra(extra, usage) ? "in_use" : "free" };
};
