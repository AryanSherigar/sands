import React from "react";
import { visibleStatsSections } from "../../lib/statsSections";
import { BenchmarksPanel } from "./BenchmarksPanel";
import { EngagementPanel } from "./EngagementPanel";
import { FunnelPanel } from "./FunnelPanel";
import { HeatmapPanel } from "./HeatmapPanel";
import { OutcomesPanel } from "./OutcomesPanel";
import { PlaysPanel } from "./PlaysPanel";
import { ReviewsPanel } from "./ReviewsPanel";
import { ScenarioStatsNav } from "./ScenarioStatsNav";
import { ShareStoryButton } from "./ShareStoryButton";
import { StatsNotice } from "./StatsNotice";
import { VersionsPanel } from "./VersionsPanel";
import type { ScenarioStatsSectionsProps } from "./ScenarioStatsSections.types";

export const ScenarioStatsSections: React.FC<ScenarioStatsSectionsProps> = ({ stats }) => (
  <div className="grid gap-8 lg:grid-cols-[12rem_minmax(0,1fr)]">
    <ScenarioStatsNav sections={visibleStatsSections(stats)} />
    <div className="flex min-w-0 flex-col gap-12">
      {!stats.is_sample_sufficient && (
        <StatsNotice
          title="Not enough plays yet"
          description={`Stats appear after ${stats.sample_threshold} plays.`}
        >
          <ShareStoryButton scenarioId={stats.scenario.scenario_id} />
        </StatsNotice>
      )}
      <PlaysPanel stats={stats} />
      {stats.outcomes && (
        <OutcomesPanel
          outcomes={stats.outcomes}
          isSampleSufficient={stats.is_sample_sufficient}
        />
      )}
      <EngagementPanel
        engagement={stats.engagement}
        isSampleSufficient={stats.is_sample_sufficient}
      />
      <FunnelPanel funnel={stats.funnel} isSampleSufficient={stats.is_sample_sufficient} />
      <ReviewsPanel
        reviews={stats.reviews}
        isSampleSufficient={stats.is_sample_sufficient}
      />
      {stats.versions.length > 0 && (
        <VersionsPanel versions={stats.versions} mode={stats.scenario.mode} />
      )}
      {stats.benchmarks && <BenchmarksPanel benchmarks={stats.benchmarks} />}
      {stats.is_sample_sufficient && stats.heatmap.length > 0 && (
        <HeatmapPanel maps={stats.heatmap} />
      )}
    </div>
  </div>
);
