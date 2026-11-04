import type {
  ExchangeReport,
  LossEstimate,
  OutlookBasis,
  TacticalOddsEstimate,
} from "../StrategyWarCouncil.types";
import { CommanderDuelCards, type CommanderProfile } from "./CommanderDuelCards";
import { EngagementChronicle, type EngagementPrediction } from "./EngagementChronicle";
import { OddsLedger } from "./OddsLedger";

export interface WarCouncilLeftRailProps {
  playerCommander: CommanderProfile | null;
  enemyCommander: CommanderProfile | null;
  odds: TacticalOddsEstimate | null;
  playerFactionName: string;
  enemyFactionName: string;
  reports: ExchangeReport[];
  activeDoctrineName: string;
}

function formatLossRange(loss: LossEstimate): string {
  return `−${loss.expected.toLocaleString()} (${loss.low.toLocaleString()}–${loss.high.toLocaleString()})`;
}

const BASIS_NOTES: Record<OutlookBasis, string> = {
  scouted_composition: "Based on your scouts' report of their troop mix.",
  assumed_even_mix: "Their troop mix is unscouted, so an even mix is assumed.",
};

function buildPrediction(odds: TacticalOddsEstimate): EngagementPrediction {
  return {
    title: "Next exchange",
    friendlyLosses: formatLossRange(odds.playerLoss),
    enemyLosses: formatLossRange(odds.enemyLoss),
    note: `${BASIS_NOTES[odds.basis]} Scout confidence: ${odds.confidence}.`,
  };
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
      {odds && <OddsLedger odds={odds} playerFactionName={playerFactionName} enemyFactionName={enemyFactionName} />}
      <EngagementChronicle
        reports={reports}
        activeDoctrineName={activeDoctrineName}
        prediction={odds ? buildPrediction(odds) : null}
      />
    </aside>
  );
}
