import { isAxiosError } from "axios";
import { apiClient } from "@/shared/lib/api-client";
import type { MapGenerationJob } from "../types/mapGeneration.types";

const HTTP_NOT_FOUND = 404;

const mapGenerationPath = (scenarioId: string): string =>
  `/v1/scenarios/${scenarioId}/strategy-map`;

export const startMapGeneration = async (
  scenarioId: string,
  description: string,
): Promise<MapGenerationJob> => {
  const response = await apiClient.post<MapGenerationJob>(
    `${mapGenerationPath(scenarioId)}/generate`,
    { description },
  );
  return response.data;
};

export const getLatestMapGenerationJob = async (
  scenarioId: string,
): Promise<MapGenerationJob | null> => {
  try {
    const response = await apiClient.get<MapGenerationJob>(
      `${mapGenerationPath(scenarioId)}/jobs/latest`,
    );
    return response.data;
  } catch (error) {
    if (isAxiosError(error) && error.response?.status === HTTP_NOT_FOUND) return null;
    throw error;
  }
};
