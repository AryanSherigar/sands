import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchScenarios } from "@/shared/api/scenarios.api";
import type { ScenarioListResponse } from "@/shared/types/scenarioSummary.types";
import {
  LANDING_ROW_LIMIT,
  LANDING_STALE_TIME_MS,
} from "../constants/landing.constants";
import type { LandingRowConfig } from "../types/landing.types";

interface UseLandingRowOptions {
  genres?: string[];
  isEnabled?: boolean;
}

export const useLandingRow = (
  row: LandingRowConfig,
  { genres, isEnabled = true }: UseLandingRowOptions = {},
): UseQueryResult<ScenarioListResponse, Error> =>
  useQuery<ScenarioListResponse, Error>({
    queryKey: ["landing-scenarios", row.id, genres ?? []],
    queryFn: () =>
      fetchScenarios({
        sort: row.sort,
        limit: LANDING_ROW_LIMIT,
        genre_tags: genres,
      }),
    staleTime: LANDING_STALE_TIME_MS,
    enabled: isEnabled,
  });
