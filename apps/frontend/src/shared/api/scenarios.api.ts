import { apiClient } from "@/shared/lib/api-client";
import type {
  GetScenariosParams,
  ScenarioListResponse,
} from "@/shared/types/scenarioSummary.types";

export const fetchScenarios = async (
  params?: GetScenariosParams,
): Promise<ScenarioListResponse> => {
  const response = await apiClient.get<ScenarioListResponse>("/v1/scenarios", {
    params,
  });
  return response.data;
};

export const toggleBookmarkApi = async (
  scenarioId: string,
): Promise<{ is_bookmarked: boolean }> => {
  const response = await apiClient.post<{ is_bookmarked: boolean }>(
    `/v1/scenarios/${scenarioId}/bookmark`,
  );
  return response.data;
};
