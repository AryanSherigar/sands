import type { FC } from "react";
import { SovereignBadge } from "./SovereignBadge";
import { TopCanopyControls } from "./TopCanopyControls";
import { StrategyLetterShelfPill } from "./StrategyLetterShelfPill";
import { StrategyReplayAuditPill } from "./StrategyReplayAuditPill";
import type { StrategyTopCanopyProps } from "./StrategyTopCanopy.types";

function CrisesPill({
  count,
  onToggle,
}: {
  count: number;
  onToggle?: () => void;
}) {
  if (count <= 0) return null;
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex items-center gap-1.5 px-3 py-1 bg-tertiary-fixed text-on-tertiary-fixed-variant rounded-full hover:brightness-95 transition text-xs font-bold"
    >
      <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
      <span>
        {count} Active {count === 1 ? "Crisis" : "Crises"}
      </span>
    </button>
  );
}

export const StrategyTopCanopy: FC<StrategyTopCanopyProps> = ({
  world,
  activeMapMode = "political",
  onSelectMapMode,
  activeCrisesCount = 0,
  onToggleSituations,
  letterDispatchNumber,
  onOpenLetter,
  onOpenTreasury,
  playthroughId,
  onReplayVerified,
  isHistoryAvailable = false,
  isHistoryActive = false,
  onToggleHistory,
  activeEdict,
  onIssueProclamation,
}) => (
  <header className="fixed top-3 inset-x-3 z-40 flex flex-wrap items-start justify-between gap-2 pointer-events-none sm:top-4 sm:inset-x-4">
    <SovereignBadge name={world?.ruler?.name} />
    <div className="flex min-w-0 max-w-full flex-wrap items-center justify-end gap-2 pointer-events-auto">
      {letterDispatchNumber !== undefined && onOpenLetter && (
        <StrategyLetterShelfPill
          dispatchNumber={letterDispatchNumber}
          onClick={onOpenLetter}
        />
      )}
      <CrisesPill
        count={activeCrisesCount}
        onToggle={onToggleSituations}
      />
      {isHistoryAvailable && onToggleHistory ? (
        <button
          type="button"
          aria-pressed={isHistoryActive}
          onClick={onToggleHistory}
          className="rounded-full border border-[#3A3128]/20 bg-[#F7F0DC]/90 px-3 py-1 text-xs font-bold text-[#3A3128] shadow-sm hover:bg-[#FAF0E6] aria-pressed:bg-[#46606E] aria-pressed:text-white cursor-pointer"
        >
          History
        </button>
      ) : null}
      <StrategyReplayAuditPill
        playthroughId={playthroughId}
        throughTurn={world?.turn}
        onVerified={onReplayVerified}
      />
      <TopCanopyControls
        world={world}
        activeMapMode={activeMapMode}
        onSelectMapMode={onSelectMapMode}
        onOpenTreasury={onOpenTreasury}
        activeEdict={activeEdict}
        onIssueProclamation={onIssueProclamation}
      />
    </div>
  </header>
);
