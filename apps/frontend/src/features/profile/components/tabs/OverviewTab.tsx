import React from "react";
import { useProfileOverview } from "../../hooks/useProfileOverview";
import { ContinueRow } from "../overview/ContinueRow/ContinueRow";
import { LifetimeStats } from "../overview/LifetimeStats/LifetimeStats";
import { RecentMilestones } from "../overview/RecentMilestones/RecentMilestones";
import { WeeklyActivityDots } from "../overview/WeeklyActivityDots/WeeklyActivityDots";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";

export const OverviewTab: React.FC = () => {
  const { data, isLoading, isError } = useProfileOverview();

  if (isLoading) return <TabSkeleton />;
  if (isError || !data) {
    return <TabErrorState message="Couldn't load your overview." />;
  }

  return (
    <div className="space-y-8">
      <LifetimeStats stats={data.lifetime_stats} />
      <WeeklyActivityDots activity={data.weekly_activity} />
      <ContinueRow runs={data.continue_runs} now={new Date()} />
      <RecentMilestones milestones={data.recent_milestones} />
    </div>
  );
};
