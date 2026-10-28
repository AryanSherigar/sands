import { isAxiosError } from "axios";
import { apiClient } from "@/shared/lib/api-client";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import { STRATEGY_MAP_PATH } from "../constants/regionMap";
import type { PublishReport } from "../types/strategyDocument.types";

const NOT_FOUND_STATUS = 404;

export const getStrategyMap = async (scenarioId: string): Promise<MapDocument | null> => {
  try {
    const response = await apiClient.get<MapDocument>(STRATEGY_MAP_PATH(scenarioId));
    return response.data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === NOT_FOUND_STATUS) return null;
    throw error;
  }
};

export const checkStrategyScenario = async (scenarioId: string): Promise<PublishReport> => {
  const response = await apiClient.post<PublishReport>(
    `/v1/scenarios/${scenarioId}/strategy-check`,
  );
  return response.data;
};
