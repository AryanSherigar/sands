import React from "react";
import { useProfileEndings } from "../../hooks/useProfileEndings";
import { ScenarioEndingsCard } from "../endings/ScenarioEndingsCard/ScenarioEndingsCard";
import { TabEmptyState } from "../states/TabEmptyState";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";

const EXPLORE_ACTION = { label: "Explore stories", to: "/discover" };

export const EndingsTab: React.FC = () => {
  const { data, isLoading, isError } = useProfileEndings();

  if (isLoading) return <TabSkeleton />;
  if (isError || !data) {
    return <TabErrorState message="Couldn't load your endings." />;
  }
  if (data.scenarios.length === 0) {
    return (
      <TabEmptyState
        message="Finish a story to discover endings"
        action={EXPLORE_ACTION}
      />
    );
  }

  return (
    <div className="space-y-4">
      {data.scenarios.map((story) => (
        <ScenarioEndingsCard key={story.scenario_id} story={story} />
      ))}
    </div>
  );
};
