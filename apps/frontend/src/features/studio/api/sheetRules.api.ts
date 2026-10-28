import { apiClient } from "@/shared/lib/api-client";
import {
  SheetRuleCreate,
  SheetRuleListResponse,
  SheetRuleResponse,
  SheetRuleUpdate,
} from "../types/sheetRule.types";

const base = (scenarioId: string): string =>
  `/v1/scenarios/${scenarioId}/sheet-rules`;

export const listSheetRules = async (
  scenarioId: string,
): Promise<SheetRuleListResponse> => {
  const response = await apiClient.get<SheetRuleListResponse>(base(scenarioId));
  return response.data;
};

export const createSheetRule = async (
  scenarioId: string,
  payload: SheetRuleCreate,
): Promise<SheetRuleResponse> => {
  const response = await apiClient.post<SheetRuleResponse>(
    base(scenarioId),
    payload,
  );
  return response.data;
};

export const updateSheetRule = async (
  scenarioId: string,
  ruleId: string,
  payload: SheetRuleUpdate,
): Promise<SheetRuleResponse> => {
  const response = await apiClient.patch<SheetRuleResponse>(
    `${base(scenarioId)}/${ruleId}`,
    payload,
  );
  return response.data;
};

export const deleteSheetRule = async (
  scenarioId: string,
  ruleId: string,
): Promise<void> => {
  await apiClient.delete(`${base(scenarioId)}/${ruleId}`);
};

export const reorderSheetRules = async (
  scenarioId: string,
  orderedRuleIds: string[],
): Promise<SheetRuleListResponse> => {
  const response = await apiClient.post<SheetRuleListResponse>(
    `${base(scenarioId)}/reorder`,
    { ordered_rule_ids: orderedRuleIds },
  );
  return response.data;
};
