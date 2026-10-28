import React from "react";
import { HTTP_NOT_FOUND } from "../../constants/stats";
import { ScenarioStatsSections } from "./ScenarioStatsSections";
import { StatsLoadError } from "./StatsLoadError";
import { StatsNotice } from "./StatsNotice";
import { StatsSkeleton } from "./StatsSkeleton";
import type { ScenarioStatsContentProps } from "./ScenarioStatsContent.types";

export const ScenarioStatsContent: React.FC<ScenarioStatsContentProps> = ({
  stats,
  isLoading,
  isError,
  errorStatus,
  onRetry,
}) => {
  if (isLoading) return <StatsSkeleton />;
  if (errorStatus === HTTP_NOT_FOUND) {
    return (
      <StatsNotice
        title="Story not found"
        description="This story doesn't exist, or it isn't yours."
      />
    );
  }
  if (isError || !stats) return <StatsLoadError onRetry={onRetry} />;
  if (!stats.scenario.has_stats) {
    return (
      <StatsNotice
        title="Publish this story to see stats"
        description="Stats start once the story is published."
      />
    );
  }
  return <ScenarioStatsSections stats={stats} />;
};
