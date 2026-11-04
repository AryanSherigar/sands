import type { TableRegion } from "../../../../lib/tableRegions";

export interface ClauseBuilderDialogProps {
  regions?: TableRegion[];
  onUse: (sentence: string) => void;
  onCancel: () => void;
}
