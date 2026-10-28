import type {
  ActiveFilterChip,
  DiscoverSort,
  DiscoverView,
} from "../../types/discover.types";

export interface ResultsHeaderProps {
  query: string;
  totalCount: number;
  chips: ActiveFilterChip[];
  sort: DiscoverSort;
  view: DiscoverView;
  onRemoveChip: (chipId: string) => void;
  onClearAll: () => void;
  onSortChange: (next: DiscoverSort) => void;
  onViewChange: (next: DiscoverView) => void;
}
