import type { BattleReportItem } from "../../../types/turnReport.types";

export interface BattleReportCardProps {
  battle: BattleReportItem;
  onFocusMap?: (regionId: string) => void;
}
