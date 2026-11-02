import type {
  EstimatedSection,
  TurnReportQuickStats,
} from "../../../types/turnReport.types";

export interface QuickStatsTickerProps {
  stats: TurnReportQuickStats;
  estimatedSections?: EstimatedSection[];
}
