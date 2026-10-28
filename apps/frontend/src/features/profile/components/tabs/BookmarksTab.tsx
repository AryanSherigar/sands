import React from "react";
import { IconX } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchScenarios } from "@/features/play/api/discovery.api";
import { toggleBookmarkApi } from "@/features/play/api/scenarioFocus.api";
import { Button } from "@/shared/components/ui/Button";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { ScenarioMiniCard } from "../cards/ScenarioMiniCard";
import { TabEmptyState } from "../states/TabEmptyState";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";

const EXPLORE_ACTION = { label: "Explore stories", to: "/discover" };

export const BookmarksTab: React.FC = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["profile-bookmarks"],
    queryFn: () => fetchScenarios({ saved: true }),
  });
  const removeMutation = useMutation({
    mutationFn: (scenarioId: string) => toggleBookmarkApi(scenarioId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["profile-bookmarks"] }),
  });

  if (isLoading) return <TabSkeleton />;
  if (isError) return <TabErrorState message="Couldn't load saved stories." />;

  const items = data?.items ?? [];
  if (items.length === 0) {
    return <TabEmptyState message="Nothing saved yet" action={EXPLORE_ACTION} />;
  }

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
      {items.map((scenario) => (
        <ScenarioMiniCard
          key={scenario.scenario_id}
          scenario={scenario}
          overlayAction={
            <Button
              variant="secondary"
              size="sm"
              aria-label="Remove bookmark"
              onClick={() => removeMutation.mutate(scenario.scenario_id)}
            >
              <IconX size={16} stroke={1.5} aria-hidden="true" />
            </Button>
          }
          footerAction={
            <ButtonLink
              to={`/setup/${scenario.scenario_id}`}
              variant="ghost"
              size="sm"
            >
              Play
            </ButtonLink>
          }
        />
      ))}
    </div>
  );
};
