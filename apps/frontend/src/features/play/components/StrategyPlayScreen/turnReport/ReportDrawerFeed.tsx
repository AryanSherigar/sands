import React from "react";
import type { ReportDrawerFeedProps } from "./ReportDrawerFeed.types";
import { BattleReportCard } from "./BattleReportCard";
import { EconomyLedgerCard } from "./EconomyLedgerCard";
import { ReportItemCard } from "./ReportItemCard";

const EmptyFeedState: React.FC = () => (
  <div className="text-center py-12 px-4 text-xs text-[#7A6F62] italic bg-[#F3EAD3]/30 rounded-lg border border-[#3A3128]/10">
    No events recorded for this category.
  </div>
);

export const ReportDrawerFeed: React.FC<ReportDrawerFeedProps> = ({
  report,
  activeFilter,
  onFocusMap,
}) => {
  const shouldShowMilitary =
    activeFilter === "all" || activeFilter === "military";
  const shouldShowEconomy =
    (activeFilter === "all" || activeFilter === "economy") &&
    report.economyLines.length > 0;

  const filteredItems = report.items.filter(
    (item) => activeFilter === "all" || item.category === activeFilter,
  );

  const displayedBattles = shouldShowMilitary ? report.battles : [];
  const hasContent =
    displayedBattles.length > 0 || shouldShowEconomy || filteredItems.length > 0;

  if (!hasContent) {
    return (
      <div className="flex-1 p-4 overflow-y-auto">
        <EmptyFeedState />
      </div>
    );
  }

  return (
    <div className="flex-1 p-4 space-y-3 overflow-y-auto">
      {displayedBattles.map((battle) => (
        <BattleReportCard
          key={battle.id}
          battle={battle}
          onFocusMap={onFocusMap}
        />
      ))}

      {shouldShowEconomy ? (
        <EconomyLedgerCard
          lines={report.economyLines}
          netGold={report.quickStats.netGold}
        />
      ) : null}

      {filteredItems.map((item) => (
        <ReportItemCard
          key={item.id}
          item={item}
          onFocusMap={onFocusMap}
        />
      ))}
    </div>
  );
};
