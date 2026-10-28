import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchScenarios } from "@/features/play/api/discovery.api";
import { ButtonLink } from "@/shared/components/ui/ButtonLink";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import { filterCreations, type CreationsFilter } from "../../lib/creations";
import { SegmentedControl } from "../SegmentedControl/SegmentedControl";
import { TabEmptyState } from "../states/TabEmptyState";
import { TabErrorState } from "../states/TabErrorState";
import { TabSkeleton } from "../states/TabSkeleton";
import { CreationsGrid } from "./CreationsGrid";
import type { CreationsTabProps } from "./CreationsTab.types";

const FILTER_OPTIONS: { value: CreationsFilter; label: string }[] = [
  { value: "published", label: "Published" },
  { value: "drafts", label: "Drafts" },
];

const CREATE_ACTION = { label: "New Story", to: "/studio/new" };

export const CreationsTab: React.FC<CreationsTabProps> = ({
  userId,
  isOwner,
}) => {
  const [filter, setFilter] = useState<CreationsFilter>("published");
  const isAlphaMode = useIsAlphaMode();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["profile-creations", userId, isOwner ? "mine" : "public"],
    queryFn: () =>
      fetchScenarios(isOwner ? { mine: true } : { creator_id: userId }),
  });

  if (isLoading) return <TabSkeleton />;
  if (isError) return <TabErrorState message="Couldn't load creations." />;

  const items = filterCreations(data?.items ?? [], isOwner, filter);
  const canCreate = isOwner && filter === "published" && !isAlphaMode;

  return (
    <div className="space-y-6">
      {isOwner && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SegmentedControl
            ariaLabel="Creations filter"
            options={FILTER_OPTIONS}
            value={filter}
            onChange={setFilter}
          />
          {!isAlphaMode && (
            <ButtonLink to="/studio" variant="secondary" size="sm">
              Manage in Studio
            </ButtonLink>
          )}
        </div>
      )}
      {items.length === 0 ? (
        <TabEmptyState
          message="No stories yet"
          action={canCreate ? CREATE_ACTION : undefined}
        />
      ) : (
        <CreationsGrid items={items} />
      )}
    </div>
  );
};
