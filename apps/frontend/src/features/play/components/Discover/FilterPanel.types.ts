import type { DiscoverFilters } from "../../types/discover.types";

export interface FilterPanelProps {
  filters: DiscoverFilters;
  hasActiveFilters: boolean;
  isAuthenticated: boolean;
  onChange: (next: DiscoverFilters) => void;
  onClearAll: () => void;
  onSignIn: () => void;
}
