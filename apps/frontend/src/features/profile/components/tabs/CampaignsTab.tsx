import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PostRunSurvey } from "@/shared/components/alpha-survey/PostRunSurvey/PostRunSurvey";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { useAbandonPlaythrough } from "../../hooks/useAbandonPlaythrough";
import { useUserPlaythroughs } from "../../hooks/useUserPlaythroughs";
import { CampaignCard } from "../cards/CampaignCard";
import { SegmentedControl } from "../SegmentedControl/SegmentedControl";
import { TabEmptyState } from "../states/TabEmptyState";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";

type CampaignFilter = "all" | "active" | "completed";

const FILTER_OPTIONS: { value: CampaignFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
];

const SCENARIO_FILTER_PARAM = "scenario";

const EXPLORE_ACTION = { label: "Explore stories", to: "/discover" };

export const CampaignsTab: React.FC = () => {
  const [filter, setFilter] = useState<CampaignFilter>("all");
  const [searchParams] = useSearchParams();
  const scenarioFilterId = searchParams.get(SCENARIO_FILTER_PARAM);
  const { data, isLoading, isError } = useUserPlaythroughs(
    filter === "all" ? undefined : filter,
  );
  const abandonMutation = useAbandonPlaythrough();
  const isAlphaMode = useIsAlphaMode();
  const [surveyPlaythroughId, setSurveyPlaythroughId] = useState<string | null>(null);

  const handleAbandon = (playthroughId: string): void => {
    abandonMutation.mutate(playthroughId, {
      onSuccess: () => {
        if (isAlphaMode) setSurveyPlaythroughId(playthroughId);
      },
    });
  };

  if (isLoading) return <TabSkeleton />;
  if (isError) return <TabErrorState message="Couldn't load campaigns." />;

  const allItems = data ?? [];
  const items = scenarioFilterId
    ? allItems.filter((campaign) => campaign.scenario_id === scenarioFilterId)
    : allItems;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SegmentedControl
          ariaLabel="Campaigns filter"
          options={FILTER_OPTIONS}
          value={filter}
          onChange={setFilter}
        />
        {items.length > 0 && (
          <ButtonLink to={EXPLORE_ACTION.to} variant="secondary" size="sm">
            {EXPLORE_ACTION.label}
          </ButtonLink>
        )}
      </div>
      {items.length === 0 ? (
        <TabEmptyState message="No runs yet" action={EXPLORE_ACTION} />
      ) : (
        <div className="space-y-4">
          {items.map((campaign) => (
            <CampaignCard
              key={campaign.playthrough_id}
              campaign={campaign}
              onAbandon={handleAbandon}
              isAbandoning={abandonMutation.isPending}
            />
          ))}
        </div>
      )}
      {surveyPlaythroughId && (
        <PostRunSurvey
          playthroughId={surveyPlaythroughId}
          isOpen
          onClose={() => setSurveyPlaythroughId(null)}
        />
      )}
    </div>
  );
};
