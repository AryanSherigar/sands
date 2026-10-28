import { useQuery } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { apiClient } from "@/shared/lib/api-client";
import type { MapDocument } from "@/shared/types/strategy-map.types";

const NOT_FOUND_STATUS = 404;

export const getStrategyMap = async (scenarioId: string): Promise<MapDocument | null> => {
  try {
    const { data } = await apiClient.get<MapDocument>(`/v1/scenarios/${scenarioId}/strategy-map`);
    return data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === NOT_FOUND_STATUS) return null;
    throw error;
  }
};

export const useStrategyMap = (scenarioId?: string) =>
  useQuery<MapDocument | null, Error>({
    queryKey: ["strategy-map", scenarioId],
    queryFn: () => getStrategyMap(scenarioId!),
    enabled: Boolean(scenarioId),
    staleTime: 0,
  });
