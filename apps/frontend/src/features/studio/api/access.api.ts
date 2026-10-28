import { apiClient } from "@/shared/lib/api-client";
import {
  ScenarioAccessMember,
  ScenarioInviteAcceptResponse,
  ScenarioInviteResponse,
} from "../types/access.types";

export const listScenarioAccess = async (
  scenarioId: string,
): Promise<ScenarioAccessMember[]> => {
  const response = await apiClient.get<ScenarioAccessMember[]>(
    `/v1/scenarios/${scenarioId}/access`,
  );
  return response.data;
};

export const removeScenarioAccess = async (
  scenarioId: string,
  userId: string,
): Promise<void> => {
  await apiClient.delete(`/v1/scenarios/${scenarioId}/access/${userId}`);
};

export const createScenarioInvite = async (
  scenarioId: string,
): Promise<ScenarioInviteResponse> => {
  const response = await apiClient.post<ScenarioInviteResponse>(
    `/v1/scenarios/${scenarioId}/invites`,
  );
  return response.data;
};

export const acceptScenarioInvite = async (
  token: string,
): Promise<ScenarioInviteAcceptResponse> => {
  const response = await apiClient.post<ScenarioInviteAcceptResponse>(
    `/v1/invites/${token}/accept`,
  );
  return response.data;
};
