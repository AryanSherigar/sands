import {
  buildDispatches,
  buildTacticalRounds,
  deriveHeadline,
  getWarScoreDelta,
} from "./turnReportAdapter";
import type {
  BattleOutcome,
  BattleReportItem,
  EconomyLedgerLine,
  EstimatedSection,
  ItemTone,
  ReportItem,
  StrategyTurnReportData,
  TacticalRound,
} from "../types/turnReport.types";
import { isEventLine, toEventReportItem } from "./eventReportItems";
import type { CampaignWorldView } from "../types/simulation.types";
import type {
  ApiBattleReport,
  ApiEconomyLine,
  ApiReportLine,
  TurnReportResponse,
} from "../types/turnReportApi.types";

const STILL_ESTIMATED_SECTIONS: EstimatedSection[] = [
  "stability_delta",
  "war_score",
  "rival_casualties",
  "tactical_round_text",
  "diplomacy_dispatches",
];

const ECONOMY_LABELS: Record<string, string> = {
  income_collected: "Provincial Taxes",
  upkeep_paid: "Military Upkeep",
  loan_interest_paid: "Loan Interest",
  loan_taken: "Loan Granted",
  loan_repaid: "Loan Repayment",
  army_raised: "Levy Recruitment",
};

interface EventPresentation {
  category: ReportItem["category"];
  title: string;
  description: string;
  tone: ItemTone;
}

const EVENT_PRESENTATION: Record<string, EventPresentation> = {
  tax_rate_set: {
    category: "internal",
    title: "Tax Policy Changed",
    description: "The crown revised the realm's tax rate.",
    tone: "neutral",
  },
  army_raised: {
    category: "military",
    title: "Levies Raised",
    description: "New troops were mustered into service.",
    tone: "positive",
  },
  army_deserted: {
    category: "military",
    title: "Desertions",
    description: "Troops slipped away from the host.",
    tone: "warning",
  },
  army_unpaid: {
    category: "military",
    title: "Unpaid Troops",
    description: "An army went without pay and morale suffered.",
    tone: "danger",
  },
  army_disbanded: {
    category: "military",
    title: "Army Disbanded",
    description: "An army was stood down and its men sent home.",
    tone: "neutral",
  },
  loan_overdue: {
    category: "economy",
    title: "Loan Overdue",
    description: "A loan payment was missed.",
    tone: "danger",
  },
  faction_defaulted: {
    category: "economy",
    title: "Default Declared",
    description: "The treasury defaulted on its debts.",
    tone: "danger",
  },
  shortfall_resolved: {
    category: "economy",
    title: "Treasury Shortfall Settled",
    description: "A shortfall in the treasury was resolved.",
    tone: "warning",
  },
};

const SURRENDER_OUTCOMES = new Set(["attacker_surrender", "defender_surrender"]);

export function mapApiOutcome(report: ApiBattleReport): BattleOutcome {
  const { outcome, own_side: ownSide } = report;
  if (!outcome || outcome.startsWith("mutual")) return "stalemate";
  const isAttackerWin = outcome === "attacker_victory" || outcome === "defender_surrender";
  const didOwnSideWin = isAttackerWin === (ownSide === "attacker");
  if (!didOwnSideWin) return "defeat";
  return SURRENDER_OUTCOMES.has(outcome) ? "decisive_victory" : "marginal_victory";
}

function toEconomyLine(line: ApiEconomyLine): EconomyLedgerLine {
  const taxPercent = line.inputs.tax_percent;
  return {
    label: ECONOMY_LABELS[line.kind] ?? line.kind.replace(/_/g, " "),
    amount: line.amount,
    category: line.category,
    details: taxPercent === undefined ? undefined : `${taxPercent}% tax rate`,
  };
}

function sumLosses(losses: ApiBattleReport["own_losses"]): number {
  return Object.values(losses).reduce((sum, count) => sum + (count ?? 0), 0);
}

function buildRounds(report: ApiBattleReport, outcome: BattleOutcome): TacticalRound[] {
  return buildTacticalRounds(report.exchanges, outcome).map((round, index) => ({
    ...round,
    varnCasualties: report.rounds[index]?.own_losses ?? round.varnCasualties,
  }));
}

function toBattleItem(
  report: ApiBattleReport,
  regionNames: Record<string, string>,
): BattleReportItem {
  const regionName = regionNames[report.region_id] ?? report.region_id;
  const outcome = mapApiOutcome(report);
  const rounds = buildRounds(report, outcome);
  const isVictory = outcome.includes("victory");
  return {
    id: report.battle_id,
    name: `Battle of ${regionName}`,
    regionId: report.region_id,
    regionName,
    outcome,
    summary: isVictory
      ? `Forces engaged and secured the field at ${regionName}.`
      : `Clashed with hostile army at ${regionName}.`,
    rounds,
    varnLosses: sumLosses(report.own_losses),
    rivalLosses: rounds.reduce((sum, round) => sum + (round.rivalCasualties ?? 0), 0),
    warScoreDelta: getWarScoreDelta(outcome),
  };
}

function toEventItems(lines: ApiReportLine[], regionNames: Record<string, string>): ReportItem[] {
  return lines.flatMap((line, index) => {
    if (isEventLine(line)) return [toEventReportItem(line, index, regionNames)];
    const presentation = EVENT_PRESENTATION[line.kind];
    if (!presentation) return [];
    return [
      {
        id: `event-${line.kind}-${index}`,
        category: presentation.category,
        title: presentation.title,
        description: presentation.description,
        badge: { label: presentation.title, tone: presentation.tone },
      },
    ];
  });
}

export function mergeTurnReport(
  estimated: StrategyTurnReportData,
  api: TurnReportResponse,
  world: CampaignWorldView,
  regionNames: Record<string, string>,
): StrategyTurnReportData {
  const battles = api.battles.map((battle) => toBattleItem(battle, regionNames));
  const quickStats = {
    ...estimated.quickStats,
    netGold: api.net_gold,
    totalCasualties: battles.reduce((sum, battle) => sum + battle.varnLosses, 0),
  };
  const dispatches = buildDispatches(null, world, regionNames, battles);
  const estimatedSections = [...STILL_ESTIMATED_SECTIONS];
  if (battles.length > 0) estimatedSections.push("victory_margin");
  return {
    ...estimated,
    headline: deriveHeadline(battles, quickStats),
    quickStats,
    battles,
    economyLines: api.economy.map(toEconomyLine),
    items: [...toEventItems(api.lines, regionNames), ...dispatches],
    estimatedSections,
  };
}
