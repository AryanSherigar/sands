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

const useEscapeKeyClose = (isOpen: boolean, onClose: () => void): void => {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);
};

const useTurnReportStoreState = () => ({
  isTurnReportOpen: useStrategyPlayStore((state) => state.isTurnReportOpen),
  latestReport: useStrategyPlayStore((state) => state.latestReport),
  activeReportFilter: useStrategyPlayStore((state) => state.activeReportFilter),
  autoShowTurnReport: useStrategyPlayStore((state) => state.autoShowTurnReport),
  closeTurnReport: useStrategyPlayStore((state) => state.closeTurnReport),
  setAutoShowTurnReport: useStrategyPlayStore((state) => state.setAutoShowTurnReport),
  setActiveReportFilter: useStrategyPlayStore((state) => state.setActiveReportFilter),
  focusMapLocation: useStrategyPlayStore((state) => state.focusMapLocation),
});

export const useTurnReportDrawer = (
  onContinue?: () => void,
  onFocusMap?: (regionId: string) => void,
): UseTurnReportDrawerResult => {
  const store = useTurnReportStoreState();
  useEscapeKeyClose(store.isTurnReportOpen, store.closeTurnReport);

  const counts = useMemo(
    () => (store.latestReport ? calculateCounts(store.latestReport) : EMPTY_COUNTS),
    [store.latestReport],
  );

  return {
    isTurnReportOpen: store.isTurnReportOpen,
    latestReport: store.latestReport,
    activeReportFilter: store.activeReportFilter,
    autoShowTurnReport: store.autoShowTurnReport,
    counts,
    handleClose: store.closeTurnReport,
    handleSelectFilter: store.setActiveReportFilter,
    handleToggleAutoShow: store.setAutoShowTurnReport,
    handleFocusMap: (regionId: string) => {
      store.focusMapLocation(regionId);
      onFocusMap?.(regionId);
    },
    handleContinue: () => {
      store.closeTurnReport();
      onContinue?.();
    },
  };
};
