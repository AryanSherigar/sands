import type { FilterPanelProps } from "./FilterPanel.types";

export interface FilterSidebarProps extends FilterPanelProps {
  isSurpriseDisabled: boolean;
  onSurprise: () => void;
}
