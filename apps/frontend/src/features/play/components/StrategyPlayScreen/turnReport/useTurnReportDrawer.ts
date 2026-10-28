import { useEffect, useMemo } from "react";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import type { StrategyTurnReportData } from "../../../types/turnReport.types";
import type { ReportCategoryCounts } from "./ReportFilterPills.types";
import type { UseTurnReportDrawerResult } from "./useTurnReportDrawer.types";

const EMPTY_COUNTS: ReportCategoryCounts = {
  all: 0,
  military: 0,
  economy: 0,
  diplomacy: 0,
  internal: 0,
};

const calculateCounts = (report: StrategyTurnReportData): ReportCategoryCounts => {
  const milItems = report.items.filter((item) => item.category === "military").length;
  const ecoItems = report.items.filter((item) => item.category === "economy").length;
  const dipItems = report.items.filter((item) => item.category === "diplomacy").length;
  const intItems = report.items.filter((item) => item.category === "internal").length;

  return {
    all: report.battles.length + (report.economyLines.length > 0 ? 1 : 0) + report.items.length,
    military: report.battles.length + milItems,
    economy: (report.economyLines.length > 0 ? 1 : 0) + ecoItems,
    diplomacy: dipItems,
    internal: intItems,
  };
};

export const useTurnReportDrawer = (
  onContinue?: () => void,
  onFocusMap?: (regionId: string) => void,
): UseTurnReportDrawerResult => {
  const isTurnReportOpen = useStrategyPlayStore((state) => state.isTurnReportOpen);
  const latestReport = useStrategyPlayStore((state) => state.latestReport);
  const activeReportFilter = useStrategyPlayStore((state) => state.activeReportFilter);
  const autoShowTurnReport = useStrategyPlayStore((state) => state.autoShowTurnReport);
  const closeTurnReport = useStrategyPlayStore((state) => state.closeTurnReport);
  const setAutoShowTurnReport = useStrategyPlayStore((state) => state.setAutoShowTurnReport);
  const setActiveReportFilter = useStrategyPlayStore((state) => state.setActiveReportFilter);
  const focusMapLocation = useStrategyPlayStore((state) => state.focusMapLocation);

  useEffect(() => {
    if (!isTurnReportOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeTurnReport();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isTurnReportOpen, closeTurnReport]);

  const counts = useMemo(
    () => (latestReport ? calculateCounts(latestReport) : EMPTY_COUNTS),
    [latestReport],
  );

  return {
    isTurnReportOpen,
    latestReport,
    activeReportFilter,
    autoShowTurnReport,
    counts,
    handleClose: closeTurnReport,
    handleSelectFilter: setActiveReportFilter,
    handleToggleAutoShow: setAutoShowTurnReport,
    handleFocusMap: (regionId: string) => {
      focusMapLocation(regionId);
      onFocusMap?.(regionId);
    },
    handleContinue: () => {
      closeTurnReport();
      onContinue?.();
    },
  };
};
