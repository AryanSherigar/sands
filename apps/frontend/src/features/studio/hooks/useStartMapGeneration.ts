import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { startMapGeneration } from "../api/mapGeneration.api";
import type { MapGenerationJob } from "../types/mapGeneration.types";
import { MAP_GENERATION_JOB_QUERY_KEY } from "./useMapGenerationJob";

export const useStartMapGeneration = (
  scenarioId: string,
): UseMutationResult<MapGenerationJob, Error, string> => {
  const queryClient = useQueryClient();
  return useMutation<MapGenerationJob, Error, string>({
    mutationFn: (description) => startMapGeneration(scenarioId, description),
    onSuccess: (job) => queryClient.setQueryData([MAP_GENERATION_JOB_QUERY_KEY, scenarioId], job),
  });
};
