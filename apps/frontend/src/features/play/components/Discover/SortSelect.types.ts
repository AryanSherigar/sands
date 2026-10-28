import type { DiscoverSort } from "../../types/discover.types";

export interface SortSelectProps {
  value: DiscoverSort;
  onChange: (next: DiscoverSort) => void;
}
