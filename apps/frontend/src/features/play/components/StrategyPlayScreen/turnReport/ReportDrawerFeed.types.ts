import type {
  StrategyTurnReportData,
  TurnReportCategory,
} from "../../../types/turnReport.types";

export interface ReportDrawerFeedProps {
  report: StrategyTurnReportData;
  activeFilter: TurnReportCategory;
  onFocusMap?: (regionId: string) => void;
}
