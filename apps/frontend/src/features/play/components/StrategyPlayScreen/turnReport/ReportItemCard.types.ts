import type { ReportItem } from "../../../types/turnReport.types";

export interface ReportItemCardProps {
  item: ReportItem;
  onFocusMap?: (regionId: string) => void;
}
