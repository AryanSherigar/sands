import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/shared/components/ui/Button";
import { OverviewHighlights } from "./OverviewHighlights";
import { OverviewPlaysChart } from "./OverviewPlaysChart";
import { OverviewTiles } from "./OverviewTiles";
import { ScenarioStatsTable } from "./ScenarioStatsTable";
import { StatsLoadError } from "./StatsLoadError";
import { StatsNotice } from "./StatsNotice";
import { StatsSkeleton } from "./StatsSkeleton";
import type { CreatorStatsContentProps } from "./CreatorStatsContent.types";

export const CreatorStatsContent: React.FC<CreatorStatsContentProps> = ({
  overview,
  isLoading,
  isError,
  onRetry,
}) => {
  const navigate = useNavigate();
  const handleGoToStudio = (): void => {
    navigate("/studio");
  };
  if (isLoading) return <StatsSkeleton />;
  if (isError || !overview) return <StatsLoadError onRetry={onRetry} />;
  if (!overview.has_published_scenarios) {
    return (
      <StatsNotice
        title="Publish a story to see stats"
        description="Stats cover your published and archived stories."
      >
        <Button variant="primary" onClick={handleGoToStudio}>
          Go to Studio
        </Button>
      </StatsNotice>
    );
  }
  return (
    <>
      <OverviewTiles totals={overview.totals} range={overview.stats_range} />
      <OverviewPlaysChart overview={overview} />
      <OverviewHighlights highlights={overview.highlights} />
      <ScenarioStatsTable rows={overview.scenarios} range={overview.stats_range} />
    </>
  );
};
