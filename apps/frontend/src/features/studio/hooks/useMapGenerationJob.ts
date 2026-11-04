import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { getLatestMapGenerationJob } from "../api/mapGeneration.api";
import type { MapGenerationJob } from "../types/mapGeneration.types";

const POLL_INTERVAL_MS = 2000;

export const MAP_GENERATION_JOB_QUERY_KEY = "map-generation-job";

export const isMapJobActive = (job: MapGenerationJob | null | undefined): boolean =>
  job?.status === "pending" || job?.status === "running";

export const useMapGenerationJob = (
  scenarioId: string,
): UseQueryResult<MapGenerationJob | null, Error> =>
  useQuery<MapGenerationJob | null, Error>({
    queryKey: [MAP_GENERATION_JOB_QUERY_KEY, scenarioId],
    queryFn: () => getLatestMapGenerationJob(scenarioId),
    enabled: Boolean(scenarioId),
    staleTime: 0,
    refetchInterval: (query) => (isMapJobActive(query.state.data) ? POLL_INTERVAL_MS : false),
  });
