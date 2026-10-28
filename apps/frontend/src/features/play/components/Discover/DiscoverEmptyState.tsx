import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/shared/components/ui/Button";
import { useIsAlphaMode } from "@/shared/hooks/useIsAlphaMode";
import type { DiscoverEmptyStateProps } from "./DiscoverEmptyState.types";

const EmptyMessage: React.FC<{
  title: string;
  hint?: string;
  children?: React.ReactNode;
}> = ({ title, hint, children }) => (
  <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
    <p className="font-display text-lg font-semibold text-content">{title}</p>
    {hint && <p className="text-sm text-content-muted">{hint}</p>}
    {children}
  </div>
);

export const DiscoverEmptyState: React.FC<DiscoverEmptyStateProps> = ({
  filters,
  hasActiveFilters,
  onClearFilters,
  onExploreTopRated,
}) => {
  const isAlphaMode = useIsAlphaMode();
  const isLibraryOnly =
    filters.library !== null && !filters.query && filters.genres.length === 0;

  if (isLibraryOnly && filters.library === "played") {
    return (
      <EmptyMessage title="You haven't played anything yet">
        <Button onClick={onExploreTopRated}>Explore Top rated</Button>
      </EmptyMessage>
    );
  }
  if (isLibraryOnly && filters.library === "saved") {
    return (
      <EmptyMessage title="Nothing saved yet — use Save on any story" />
    );
  }
  if (isLibraryOnly && filters.library === "created") {
    return (
      <EmptyMessage title="You haven't created a story">
        {!isAlphaMode && (
          <Link
            to="/studio/new"
            className="inline-flex rounded-md border border-accent bg-accent px-4 py-2 text-sm font-medium text-accent-contrast hover:bg-accent-strong"
          >
            New Story
          </Link>
        )}
      </EmptyMessage>
    );
  }
  if (hasActiveFilters) {
    return (
      <EmptyMessage
        title="No stories match these filters"
        hint="Try removing a filter"
      >
        <Button onClick={onClearFilters}>Clear filters</Button>
      </EmptyMessage>
    );
  }
  return <EmptyMessage title="No stories yet" />;
};
