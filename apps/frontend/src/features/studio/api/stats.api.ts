import { apiClient } from "@/shared/lib/api-client";
import type {
  CreatorStatsOverviewResponse,
  ScenarioStatsResponse,
  StatsRange,
} from "../types/stats.types";

export const getCreatorStatsOverview = async (
  range: StatsRange,
): Promise<CreatorStatsOverviewResponse> => {
  const response = await apiClient.get<CreatorStatsOverviewResponse>(
    "/v1/creators/me/stats",
    { params: { range } },
  );
  return response.data;
};

export const getScenarioStats = async (
  scenarioId: string,
  range: StatsRange,
): Promise<ScenarioStatsResponse> => {
  const response = await apiClient.get<ScenarioStatsResponse>(
    `/v1/scenarios/${scenarioId}/stats`,
    { params: { range } },
  );
  return response.data;
};
