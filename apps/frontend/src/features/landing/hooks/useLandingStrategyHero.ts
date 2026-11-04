import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchScenarios } from "@/shared/api/scenarios.api";
import type { ScenarioListResponse } from "@/shared/types/scenarioSummary.types";
import {
  LANDING_STALE_TIME_MS,
  STRATEGY_HERO_LIMIT,
} from "../constants/landing.constants";

export const useLandingStrategyHero = (): UseQueryResult<
  ScenarioListResponse,
  Error
> =>
  useQuery<ScenarioListResponse, Error>({
    queryKey: ["landing-scenarios", "strategy-hero"],
    queryFn: () =>
      fetchScenarios({
        mode: "strategy",
        sort: "rating_avg",
        limit: STRATEGY_HERO_LIMIT,
      }),
    staleTime: LANDING_STALE_TIME_MS,
  });
