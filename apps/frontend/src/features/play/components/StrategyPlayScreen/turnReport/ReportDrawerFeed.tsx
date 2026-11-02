import React from "react";
import { IconAlertCircle } from "@tabler/icons-react";
import type { ReportDrawerFeedProps } from "./ReportDrawerFeed.types";
import type {
  BattleReportItem,
  EconomyLedgerLine,
  ReportItem,
  StrategyTurnReportData,
  TurnReportCategory,
} from "../../../types/turnReport.types";
import { BattleReportCard } from "./BattleReportCard";
import { EconomyLedgerCard } from "./EconomyLedgerCard";
import { ReportItemCard } from "./ReportItemCard";

const EmptyFeedState: React.FC = () => (
  <div className="text-center py-12 px-4 text-xs text-[#7A6F62] italic bg-[#F3EAD3]/30 rounded-lg border border-[#3A3128]/10">
    No events recorded for this category.
  </div>
);

const EstimatedNoticeBanner: React.FC = () => (
  <div className="p-3 bg-[#FAF3E0] border border-[#D4A373]/50 rounded text-xs text-[#5C4D3C] flex items-center gap-2">
    <IconAlertCircle size={16} className="text-[#D4A373] shrink-0" />
    <span>Dispatches delayed — seasonal ledger estimated from realm records.</span>
  </div>
);

interface FeedItemListProps {
  battles: BattleReportItem[];
  economyLines: EconomyLedgerLine[];
  items: ReportItem[];
  netGold: number;
  shouldShowEconomy: boolean;
  isEstimatedEconomy: boolean;
  onFocusMap?: (regionId: string) => void;
}

const FeedItemList: React.FC<FeedItemListProps> = ({
  battles,
  economyLines,
  items,
  netGold,
  shouldShowEconomy,
  isEstimatedEconomy,
  onFocusMap,
}) => (
  <>
    {battles.map((battle) => (
      <BattleReportCard
        key={battle.id}
        battle={battle}
        onFocusMap={onFocusMap}
      />
    ))}
    {shouldShowEconomy ? (
      <EconomyLedgerCard
        lines={economyLines}
        netGold={netGold}
        isEstimated={isEstimatedEconomy}
      />
    ) : null}
    {items.map((item) => (
      <ReportItemCard
        key={item.id}
        item={item}
        onFocusMap={onFocusMap}
      />
    ))}
  </>
);

const filterFeedContent = (
  report: StrategyTurnReportData,
  activeFilter: TurnReportCategory,
) => {
  const shouldShowMilitary =
    activeFilter === "all" || activeFilter === "military";
  const shouldShowEconomy =
    (activeFilter === "all" || activeFilter === "economy") &&
    report.economyLines.length > 0;
  const filteredItems = report.items.filter(
    (item) => activeFilter === "all" || item.category === activeFilter,
  );
  const battles = shouldShowMilitary ? report.battles : [];
  const hasContent =
    battles.length > 0 || shouldShowEconomy || filteredItems.length > 0;

  return { battles, filteredItems, shouldShowEconomy, hasContent };
};

export const ReportDrawerFeed: React.FC<ReportDrawerFeedProps> = ({
  report,
  activeFilter,
  onFocusMap,
}) => {
  const isEstimatedEconomy = Boolean(
    report.estimatedSections?.includes("economy_lines"),
  );
  const { battles, filteredItems, shouldShowEconomy, hasContent } =
    filterFeedContent(report, activeFilter);

  return (
    <div className="flex-1 p-4 space-y-3 overflow-y-auto">
      {isEstimatedEconomy ? <EstimatedNoticeBanner /> : null}
      {hasContent ? (
        <FeedItemList
          battles={battles}
          economyLines={report.economyLines}
          items={filteredItems}
          netGold={report.quickStats.netGold}
          shouldShowEconomy={shouldShowEconomy}
          isEstimatedEconomy={isEstimatedEconomy}
          onFocusMap={onFocusMap}
        />
      ) : (
        <EmptyFeedState />
      )}
    </div>
  );
};
