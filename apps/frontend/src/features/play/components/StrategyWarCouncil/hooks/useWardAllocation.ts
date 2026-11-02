import { useCallback, useState } from "react";
import type {
  RankTier,
  WardConfig,
  WardIdentifier,
} from "../StrategyWarCouncil.types";
import { buildDefaultWards } from "./warCouncilWards";

const MIN_COHORT_COUNT = 0;
const MAX_COHORT_COUNT = 10000;

const clampCount = (count: number, delta: number): number => {
  return Math.max(MIN_COHORT_COUNT, Math.min(MAX_COHORT_COUNT, count + delta));
};

const updateWardCohort = (
  wardConfig: WardConfig,
  rank: RankTier,
  delta: number,
): WardConfig => ({
  ...wardConfig,
  ranks: wardConfig.ranks.map((cohort) =>
    cohort.rankOrder === rank
      ? { ...cohort, count: clampCount(cohort.count, delta) }
      : cohort,
  ),
});

const swapWardRanks = (
  wardConfig: WardConfig,
  fromRank: RankTier,
  toRank: RankTier,
): WardConfig => {
  if (fromRank === toRank) return wardConfig;
  return {
    ...wardConfig,
    ranks: wardConfig.ranks.map((cohort) => {
      if (cohort.rankOrder === fromRank) {
        return { ...cohort, rankOrder: toRank };
      }
      if (cohort.rankOrder === toRank) {
        return { ...cohort, rankOrder: fromRank };
      }
      return cohort;
    }),
  };
};

export function useWardAllocation() {
  const [wards, setWards] = useState<Record<WardIdentifier, WardConfig>>(buildDefaultWards);

  const updateCohortCount = useCallback(
    (ward: WardIdentifier, rank: RankTier, delta: number) => {
      setWards((prev) => ({
        ...prev,
        [ward]: updateWardCohort(prev[ward], rank, delta),
      }));
    },
    [],
  );

  const reorderRank = useCallback(
    (ward: WardIdentifier, fromRank: RankTier, toRank: RankTier) => {
      setWards((prev) => ({
        ...prev,
        [ward]: swapWardRanks(prev[ward], fromRank, toRank),
      }));
    },
    [],
  );

  return { wards, updateCohortCount, reorderRank };
}
