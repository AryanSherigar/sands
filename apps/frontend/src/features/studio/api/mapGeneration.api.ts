import { apiClient } from "@/shared/lib/api-client";
import { MAP_GENERATION_TIMEOUT_MS } from "../constants/upload";
import type { GeneratedMapArt, GeneratedRegionImage } from "../types/mapGeneration.types";

const generationPath = (scenarioId: string, step: "generate-regions" | "generate-art"): string =>
  `/v1/scenarios/${scenarioId}/strategy-map/${step}`;

export const generateMapRegions = async (
  scenarioId: string,
  description: string,
): Promise<GeneratedRegionImage> => {
  const response = await apiClient.post<GeneratedRegionImage>(
    generationPath(scenarioId, "generate-regions"),
    { description },
    { timeout: MAP_GENERATION_TIMEOUT_MS },
  );
  return response.data;
};

export const generateMapArt = async (
  scenarioId: string,
  regionImage: Blob,
  description: string,
): Promise<GeneratedMapArt> => {
  const formData = new FormData();
  formData.append("file", regionImage, "generated-regions.png");
  formData.append("description", description);
  const response = await apiClient.post<GeneratedMapArt>(
    generationPath(scenarioId, "generate-art"),
    formData,
    { timeout: MAP_GENERATION_TIMEOUT_MS, headers: { "Content-Type": undefined } },
  );
  return response.data;
};
