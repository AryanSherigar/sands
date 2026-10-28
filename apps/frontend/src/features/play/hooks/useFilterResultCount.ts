import { useQuery } from "@tanstack/react-query";
import { fetchScenarios } from "@/shared/api/scenarios.api";
import { DISCOVER_STALE_TIME_MS } from "../constants/discover.constants";
import type { DiscoverFilters } from "../types/discover.types";
import { toScenarioApiParams } from "../utils/discoverFilters";

const COUNT_PROBE_LIMIT = 1;

export const useFilterResultCount = (
  filters: DiscoverFilters,
  isEnabled: boolean,
): number | null => {
  const apiParams = toScenarioApiParams(filters);
  const { data } = useQuery({
    queryKey: ["scenario-count", apiParams],
    queryFn: () => fetchScenarios({ ...apiParams, limit: COUNT_PROBE_LIMIT }),
    enabled: isEnabled,
    staleTime: DISCOVER_STALE_TIME_MS,
  });
  return data?.total_count ?? null;
};
