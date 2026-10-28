import React from "react";
import {
  NEXT_PAGE_SKELETON_COUNT,
  POSTER_SKELETON_COUNT,
  ROW_SKELETON_COUNT,
} from "../../constants/discover.constants";
import { useLoadMoreTrigger } from "@/shared/hooks/useLoadMoreTrigger";
import { DiscoverErrorBanner } from "./DiscoverErrorBanner";
import { ScenarioPosterCard } from "./ScenarioPosterCard";
import { ScenarioPosterSkeleton } from "./ScenarioPosterSkeleton";
import { ScenarioRowCard } from "./ScenarioRowCard";
import { ResultsFooter } from "./ResultsFooter";
import { ScenarioRowSkeleton } from "./ScenarioRowSkeleton";
import type { DiscoverResultsProps } from "./DiscoverResults.types";

const GRID_CLASSES =
  "grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4 min-[1440px]:grid-cols-5";

const LIST_CLASSES = "flex flex-col gap-3.5";

const skeletons = (count: number, isGrid: boolean): React.ReactNode[] =>
  Array.from({ length: count }, (_, i) =>
    isGrid ? <ScenarioPosterSkeleton key={i} /> : <ScenarioRowSkeleton key={i} />,
  );

export const DiscoverResults: React.FC<DiscoverResultsProps> = ({
  list,
  view,
  emptyState,
  onToggleSave,
}) => {
  const isGrid = view === "grid";
  const sentinelRef = useLoadMoreTrigger(
    list.fetchNextPage,
    list.hasNextPage && !list.isFetchingNextPage,
  );

  if (list.isLoading) {
    const firstPageCount = isGrid ? POSTER_SKELETON_COUNT : ROW_SKELETON_COUNT;
    return <div className={isGrid ? GRID_CLASSES : LIST_CLASSES}>{skeletons(firstPageCount, isGrid)}</div>;
  }
  if (list.isError && list.items.length === 0) {
    return <DiscoverErrorBanner onRetry={list.refetch} />;
  }
  if (list.items.length === 0) return <>{emptyState}</>;

  const Card = isGrid ? ScenarioPosterCard : ScenarioRowCard;
  return (
    <div className="animate-in fade-in duration-150">
      {list.isError && <DiscoverErrorBanner onRetry={list.refetch} />}
      <div className={isGrid ? GRID_CLASSES : LIST_CLASSES}>
        {list.items.map((scenario) => (
          <Card key={scenario.scenario_id} scenario={scenario} onToggleSave={onToggleSave} />
        ))}
        {list.isFetchingNextPage && skeletons(NEXT_PAGE_SKELETON_COUNT, isGrid)}
      </div>
      <div ref={sentinelRef} className="mt-6">
        <ResultsFooter
          loadedCount={list.items.length}
          totalCount={list.totalCount}
          hasNextPage={list.hasNextPage}
          onLoadMore={list.fetchNextPage}
        />
      </div>
    </div>
  );
};
