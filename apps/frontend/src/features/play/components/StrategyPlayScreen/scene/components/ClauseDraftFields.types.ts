import type { ClauseDraft } from "../../../../lib/clauseSentence";
import type { TableRegion } from "../../../../lib/tableRegions";

export interface ClauseDraftFieldsProps {
  draft: ClauseDraft;
  position: number;
  regions: TableRegion[];
  canRemove: boolean;
  onChange: (change: Partial<ClauseDraft>) => void;
  onRemove: () => void;
}
