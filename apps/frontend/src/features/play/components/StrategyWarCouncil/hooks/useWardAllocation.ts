import { useCallback, useState } from "react";
import type {
  RankTier,
  WardConfig,
  WardIdentifier,
} from "../StrategyWarCouncil.types";
import { buildWardsFromContingent } from "./warCouncilWards";

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

const buildActiveTroopsKey = (activeTroops: Record<string, number>): string =>
  Object.entries(activeTroops)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([troopType, count]) => `${troopType}:${count}`)
    .join("|");

interface WardAllocationState {
  sourceKey: string;
  wards: Record<WardIdentifier, WardConfig>;
}

export function useWardAllocation(activeTroops: Record<string, number>) {
  const sourceKey = buildActiveTroopsKey(activeTroops);
  const [state, setState] = useState<WardAllocationState>(() => ({
    sourceKey,
    wards: buildWardsFromContingent(activeTroops),
  }));

  if (state.sourceKey !== sourceKey) {
    setState({ sourceKey, wards: buildWardsFromContingent(activeTroops) });
  }

  const updateCohortCount = useCallback(
    (ward: WardIdentifier, rank: RankTier, delta: number) => {
      setState((previous) => ({
        ...previous,
        wards: {
          ...previous.wards,
          [ward]: updateWardCohort(previous.wards[ward], rank, delta),
        },
      }));
    },
    [],
  );

  const reorderRank = useCallback(
    (ward: WardIdentifier, fromRank: RankTier, toRank: RankTier) => {
      setState((previous) => ({
        ...previous,
        wards: {
          ...previous.wards,
          [ward]: swapWardRanks(previous.wards[ward], fromRank, toRank),
        },
      }));
    },
    [],
  );

  return { wards: state.wards, updateCohortCount, reorderRank };
}
