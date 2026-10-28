import type { DiscoverFilters } from "../../types/discover.types";

export interface FilterSheetProps {
  isOpen: boolean;
  appliedFilters: DiscoverFilters;
  isAuthenticated: boolean;
  onApply: (next: DiscoverFilters) => void;
  onClose: () => void;
  onSignIn: () => void;
}
