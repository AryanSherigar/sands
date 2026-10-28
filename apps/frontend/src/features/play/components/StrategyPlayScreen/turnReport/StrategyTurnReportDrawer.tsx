import React from "react";
import { IconX } from "@tabler/icons-react";
import type { StrategyTurnReportDrawerProps } from "./StrategyTurnReportDrawer.types";
import { ReportDrawerHeader } from "./ReportDrawerHeader";
import { QuickStatsTicker } from "./QuickStatsTicker";
import { ReportFilterPills } from "./ReportFilterPills";
import { ReportDrawerFeed } from "./ReportDrawerFeed";
import { ReportDrawerFooter } from "./ReportDrawerFooter";
import { useTurnReportDrawer } from "./useTurnReportDrawer";

const EmptyReportFallback: React.FC<{ onClose: () => void }> = ({ onClose }) => (
  <aside className="w-[460px] absolute left-0 top-[49px] bottom-0 z-30 flex flex-col border-r border-[#3A3128]/20 bg-[#F7F0DC]/95 backdrop-blur-sm shadow-xl">
    <div className="flex justify-end p-3 border-b border-[#3A3128]/10">
      <button
        type="button"
        aria-label="Close report"
        onClick={onClose}
        className="p-1 rounded text-[#7A6F62] hover:text-[#3A3128]"
      >
        <IconX size={16} />
      </button>
    </div>
    <div className="flex-1 flex items-center justify-center p-6 text-sm text-[#7A6F62] italic">
      No turn report available.
    </div>
  </aside>
);

export const StrategyTurnReportDrawer: React.FC<StrategyTurnReportDrawerProps> = ({
  onContinue,
  onFocusMap,
}) => {
  const {
    isTurnReportOpen,
    latestReport,
    activeReportFilter,
    autoShowTurnReport,
    counts,
    handleClose,
    handleSelectFilter,
    handleToggleAutoShow,
    handleFocusMap,
    handleContinue,
  } = useTurnReportDrawer(onContinue, onFocusMap);

  if (!isTurnReportOpen) return null;
  if (!latestReport) return <EmptyReportFallback onClose={handleClose} />;

  return (
    <aside className="w-[460px] absolute left-0 top-[49px] bottom-0 z-30 flex flex-col border-r border-[#3A3128]/20 bg-[#F7F0DC]/95 backdrop-blur-sm shadow-xl">
      <ReportDrawerHeader
        turn={latestReport.turn}
        seasonTitle={latestReport.seasonTitle}
        headline={latestReport.headline}
        onClose={handleClose}
      />
      <div className="p-3 border-b border-[#3A3128]/10 bg-[#F3EAD3]/30">
        <QuickStatsTicker stats={latestReport.quickStats} />
      </div>
      <ReportFilterPills
        activeFilter={activeReportFilter}
        counts={counts}
        onSelectFilter={handleSelectFilter}
      />
      <ReportDrawerFeed
        report={latestReport}
        activeFilter={activeReportFilter}
        onFocusMap={handleFocusMap}
      />
      <ReportDrawerFooter
        autoShowTurnReport={autoShowTurnReport}
        onToggleAutoShow={handleToggleAutoShow}
        onDismiss={handleClose}
        onContinue={handleContinue}
      />
    </aside>
  );
};
