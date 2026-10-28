import React from "react";
import { CreatorStatsContent } from "../components/Stats/CreatorStatsContent";
import { RangePicker } from "../components/Stats/RangePicker";
import { useCreatorStatsOverview } from "../hooks/useCreatorStatsOverview";
import { useStatsRange } from "../hooks/useStatsRange";

export const CreatorStatsPage: React.FC = () => {
  const { range, setRange } = useStatsRange();
  const overviewQuery = useCreatorStatsOverview(range);
  const handleRetry = (): void => {
    void overviewQuery.refetch();
  };
  return (
    <div className="font-sans text-content">
      <div>
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-8 px-4 pb-16 pt-8 sm:px-6">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <h1 className="font-mono text-sm font-semibold uppercase tracking-widest text-content">
              Creator stats
            </h1>
            <RangePicker value={range} onChange={setRange} />
          </header>
          <CreatorStatsContent
            overview={overviewQuery.data}
            isLoading={overviewQuery.isLoading}
            isError={overviewQuery.isError}
            onRetry={handleRetry}
          />
        </div>
      </div>
    </div>
  );
};
