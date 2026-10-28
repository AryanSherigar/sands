import { apiClient } from "@/shared/lib/api-client";
import {
  RuleCheckCreate,
  RuleCheckListResponse,
  RuleCheckResponse,
  RuleCheckUpdate,
} from "../types/ruleCheck.types";

const base = (scenarioId: string): string =>
  `/v1/scenarios/${scenarioId}/rule-checks`;

export const listRuleChecks = async (
  scenarioId: string,
): Promise<RuleCheckListResponse> => {
  const response = await apiClient.get<RuleCheckListResponse>(base(scenarioId));
  return response.data;
};

export const createRuleCheck = async (
  scenarioId: string,
  payload: RuleCheckCreate,
): Promise<RuleCheckResponse> => {
  const response = await apiClient.post<RuleCheckResponse>(
    base(scenarioId),
    payload,
  );
  return response.data;
};

export const updateRuleCheck = async (
  scenarioId: string,
  checkId: string,
  payload: RuleCheckUpdate,
): Promise<RuleCheckResponse> => {
  const response = await apiClient.patch<RuleCheckResponse>(
    `${base(scenarioId)}/${checkId}`,
    payload,
  );
  return response.data;
};

export const deleteRuleCheck = async (
  scenarioId: string,
  checkId: string,
): Promise<void> => {
  await apiClient.delete(`${base(scenarioId)}/${checkId}`);
};

export const reorderRuleChecks = async (
  scenarioId: string,
  orderedCheckIds: string[],
): Promise<RuleCheckListResponse> => {
  const response = await apiClient.post<RuleCheckListResponse>(
    `${base(scenarioId)}/reorder`,
    { ordered_check_ids: orderedCheckIds },
  );
  return response.data;
};
