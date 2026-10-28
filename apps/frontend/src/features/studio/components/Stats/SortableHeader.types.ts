import type { ScenarioTableColumn, SortDirection } from "../../types/statsView.types";

export interface SortableHeaderProps {
  column: ScenarioTableColumn;
  isActive: boolean;
  direction: SortDirection;
  onSort: () => void;
}
