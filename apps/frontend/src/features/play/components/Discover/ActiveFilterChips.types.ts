import type { ActiveFilterChip } from "../../types/discover.types";

export interface ActiveFilterChipsProps {
  chips: ActiveFilterChip[];
  onRemove: (chipId: string) => void;
  onClearAll: () => void;
}
