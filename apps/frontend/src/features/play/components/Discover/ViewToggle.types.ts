import type { DiscoverView } from "../../types/discover.types";

export interface ViewToggleProps {
  value: DiscoverView;
  onChange: (next: DiscoverView) => void;
}
