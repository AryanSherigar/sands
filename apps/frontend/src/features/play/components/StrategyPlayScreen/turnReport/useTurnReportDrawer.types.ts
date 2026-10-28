import type {
  StrategyTurnReportData,
  TurnReportCategory,
} from "../../../types/turnReport.types";
import type { ReportCategoryCounts } from "./ReportFilterPills.types";

export interface UseTurnReportDrawerResult {
  isTurnReportOpen: boolean;
  latestReport: StrategyTurnReportData | null;
  activeReportFilter: TurnReportCategory;
  autoShowTurnReport: boolean;
  counts: ReportCategoryCounts;
  handleClose: () => void;
  handleSelectFilter: (filter: TurnReportCategory) => void;
  handleToggleAutoShow: (autoShow: boolean) => void;
  handleFocusMap: (regionId: string) => void;
  handleContinue: () => void;
}
