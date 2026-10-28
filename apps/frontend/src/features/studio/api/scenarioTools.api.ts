import { apiClient } from "@/shared/lib/api-client";
import {
  ScenarioToolsResponse,
  ScenarioToolsUpdate,
} from "../types/scenarioTools.types";

export const getScenarioTools = async (
  scenarioId: string,
): Promise<ScenarioToolsResponse> => {
  const response = await apiClient.get<ScenarioToolsResponse>(
    `/v1/scenarios/${scenarioId}/tools`,
  );
  return response.data;
};

export const updateScenarioTools = async (
  scenarioId: string,
  payload: ScenarioToolsUpdate,
): Promise<ScenarioToolsResponse> => {
  const response = await apiClient.put<ScenarioToolsResponse>(
    `/v1/scenarios/${scenarioId}/tools`,
    payload,
  );
  return response.data;
};
