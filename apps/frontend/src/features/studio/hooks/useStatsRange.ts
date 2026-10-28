import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { STATS_RANGE_PARAM } from "../constants/stats";
import { parseStatsRange } from "../lib/statsRange";
import type { StatsRange } from "../types/stats.types";

export const useStatsRange = (): {
  range: StatsRange;
  setRange: (next: StatsRange) => void;
} => {
  const [searchParams, setSearchParams] = useSearchParams();
  const range = parseStatsRange(searchParams.get(STATS_RANGE_PARAM));
  const setRange = useCallback(
    (next: StatsRange) => {
      setSearchParams(
        (previous) => {
          const params = new URLSearchParams(previous);
          params.set(STATS_RANGE_PARAM, next);
          return params;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );
  return { range, setRange };
};
