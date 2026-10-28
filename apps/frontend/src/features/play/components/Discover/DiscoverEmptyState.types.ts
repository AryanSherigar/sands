import type { DiscoverFilters } from "../../types/discover.types";

export interface DiscoverEmptyStateProps {
  filters: DiscoverFilters;
  hasActiveFilters: boolean;
  onClearFilters: () => void;
  onExploreTopRated: () => void;
}
