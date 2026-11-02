import type { ExchangeReport, TacticalOddsEstimate } from "../StrategyWarCouncil.types";
import { CommanderDuelCards, type CommanderProfile } from "./CommanderDuelCards";
import { EngagementChronicle } from "./EngagementChronicle";
import { OddsLedger } from "./OddsLedger";

export interface WarCouncilLeftRailProps {
  playerCommander: CommanderProfile | null;
  enemyCommander: CommanderProfile | null;
  odds: TacticalOddsEstimate;
  playerFactionName: string;
  enemyFactionName: string;
  reports: ExchangeReport[];
  activeDoctrineName: string;
}

export function WarCouncilLeftRail({
  playerCommander,
  enemyCommander,
  odds,
  playerFactionName,
  enemyFactionName,
  reports,
  activeDoctrineName,
}: WarCouncilLeftRailProps) {
  return (
    <aside className="w-full lg:w-[24%] lg:h-full flex flex-col bg-[#F7F0DC]/95 backdrop-blur-md border-b lg:border-b-0 lg:border-r border-[#3A3128]/15 z-20 lg:overflow-y-auto p-3.5 gap-3 shadow-md">
      <CommanderDuelCards playerCommander={playerCommander} enemyCommander={enemyCommander} />
      <OddsLedger odds={odds} playerFactionName={playerFactionName} enemyFactionName={enemyFactionName} />
      <EngagementChronicle
        reports={reports}
        activeDoctrineName={activeDoctrineName}
        prediction={{
          title: odds.balancePercent >= 55 ? "Decisive Victory Predicted" : "Contested Outcome",
          friendlyLosses: `−${odds.playerLossEstimated} Levies`,
          enemyLosses: `−${odds.enemyLossEstimated} Horse & Foot`,
          warScore: `+${odds.warScoreEstimated} War Score • Position Secured`,
        }}
      />
    </aside>
  );
}
