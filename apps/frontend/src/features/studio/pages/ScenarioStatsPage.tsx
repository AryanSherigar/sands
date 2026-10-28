import React from "react";
import { useParams } from "react-router-dom";
import { ScenarioStatsContent } from "../components/Stats/ScenarioStatsContent";
import { ScenarioStatsHeader } from "../components/Stats/ScenarioStatsHeader";
import { useScenarioStats } from "../hooks/useScenarioStats";
import { useStatsRange } from "../hooks/useStatsRange";
import { getErrorStatus } from "../lib/errorStatus";

export const ScenarioStatsPage: React.FC = () => {
  const { id = "" } = useParams<{ id: string }>();
  const { range, setRange } = useStatsRange();
  const statsQuery = useScenarioStats(id, range);
  const handleRetry = (): void => {
    void statsQuery.refetch();
  };
  return (
    <div className="font-sans text-content">
      <div>
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-8 px-4 pb-16 pt-8 sm:px-6">
          <ScenarioStatsHeader
            scenarioId={id}
            scenario={statsQuery.data?.scenario}
            range={range}
            onRangeChange={setRange}
          />
          <ScenarioStatsContent
            stats={statsQuery.data}
            isLoading={statsQuery.isLoading}
            isError={statsQuery.isError}
            errorStatus={getErrorStatus(statsQuery.error)}
            onRetry={handleRetry}
          />
        </div>
      </div>
    </div>
  );
};
