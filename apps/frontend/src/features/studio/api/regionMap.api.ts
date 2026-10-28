import { apiClient } from "@/shared/lib/api-client";
import type { MapDocument } from "@/shared/types/strategy-map.types";
import { STRATEGY_MAP_PATH } from "../constants/regionMap";

export const saveRegionMap = async (
  scenarioId: string,
  document: MapDocument,
): Promise<MapDocument> => {
  const response = await apiClient.put<MapDocument>(
    STRATEGY_MAP_PATH(scenarioId),
    document,
  );
  return response.data;
};
