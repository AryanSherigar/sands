import { ALL_ESTIMATED_SECTIONS } from "../constants/turnReportGaps";
import { deriveDate } from "./strategyClock";
import type {
  BattleOutcome,
  BattleReportItem,
  EconomyLedgerLine,
  ReportItem,
  StrategyTurnReportData,
  TacticalRound,
  TurnReportQuickStats,
} from "../types/turnReport.types";
import type {
  BattleView,
  CampaignWorldView,
  LoanState,
  RegionView,
  RivalView,
} from "../types/simulation.types";

const TAX_RATE_MULTIPLIERS: Record<string, number> = {
  low: 0.8,
  normal: 1.0,
  high: 1.25,
};

const DEFAULT_REGION_WEALTH = 30;
const MIN_TAX_INCOME = 10;
const ARMY_BASE_UPKEEP = 40;
const MIN_ARMY_UPKEEP = 20;
const HIGH_UNREST_THRESHOLD = 30;
const VICTORY_WAR_SCORE = 15;
const MARGINAL_WAR_SCORE = 8;
const DEFEAT_WAR_SCORE = -12;

function mapBattleOutcome(outcome?: string | null): BattleOutcome {
  if (!outcome) {
    return "stalemate";
  }
  const normalized = outcome.toLowerCase();
  if (normalized.includes("decisive") || normalized.endsWith("_victory")) {
    return "decisive_victory";
  }
  if (normalized.includes("victory")) {
    return "marginal_victory";
  }
  if (normalized.includes("defeat") || normalized.includes("surrender")) {
    return "defeat";
  }
  return "stalemate";
}

export function getWarScoreDelta(outcome: BattleOutcome): number {
  if (outcome === "decisive_victory") {
    return VICTORY_WAR_SCORE;
  }
  if (outcome === "marginal_victory") {
    return MARGINAL_WAR_SCORE;
  }
  if (outcome === "defeat") {
    return DEFEAT_WAR_SCORE;
  }
  return 0;
}

function createTacticalRound(
  roundIndex: number,
  isVictory: boolean,
): TacticalRound {
  if (roundIndex === 1) {
    return {
      round: 1,
      description: "Initial skirmish, archer volleys and probe attacks",
      varnCasualties: isVictory ? 28 : 55,
      rivalCasualties: isVictory ? 62 : 30,
    };
  }
  return {
    round: roundIndex,
    description: isVictory
      ? "Cavalry flank maneuver shattered enemy formation"
      : "Heavy enemy pressure broke our vanguard line",
    varnCasualties: isVictory ? 45 : 90,
    rivalCasualties: isVictory ? 120 : 40,
    outcomeNote: isVictory ? "Hostile forces routed" : "Retreat sounded",
  };
}

export function buildTacticalRounds(
  exchangesUsed: number,
  outcome: BattleOutcome,
): TacticalRound[] {
  const count = Math.max(1, exchangesUsed || 1);
  const rounds: TacticalRound[] = [];
  const isVictory =
    outcome === "decisive_victory" || outcome === "marginal_victory";

  for (let roundIndex = 1; roundIndex <= count; roundIndex += 1) {
    rounds.push(createTacticalRound(roundIndex, isVictory));
  }
  return rounds;
}

export function calculateQuickStats(
  prev: CampaignWorldView | null,
  next: CampaignWorldView,
): TurnReportQuickStats {
  const netGold = prev
    ? next.my_faction.treasury - prev.my_faction.treasury
    : 0;
  const stabilityDelta = prev
    ? next.my_faction.stability - prev.my_faction.stability
    : 0;
  const totalCasualties = prev
    ? Math.max(0, prev.my_faction.manpower - next.my_faction.manpower)
    : 0;

  return {
    netGold,
    totalCasualties,
    stability: next.my_faction.stability,
    stabilityDelta,
    manpower: next.my_faction.manpower,
  };
}

function calculateTaxIncome(world: CampaignWorldView): number {
  const rateMultiplier =
    TAX_RATE_MULTIPLIERS[world.my_faction.tax_rate] ?? 1.0;
  const owned = world.regions.filter(
    (region) =>
      region.owner_id === world.my_faction.id ||
      region.detail?.owner_id === world.my_faction.id,
  );
  const totalWealth = owned.reduce(
    (sum, region) => sum + (region.detail?.wealth ?? DEFAULT_REGION_WEALTH),
    0,
  );
  return Math.max(MIN_TAX_INCOME, Math.round(totalWealth * rateMultiplier));
}

function calculateArmyUpkeep(world: CampaignWorldView): number {
  const ownArmies = world.armies.filter(
    (army) => army.owner_id === world.my_faction.id,
  );
  return Math.max(MIN_ARMY_UPKEEP, ownArmies.length * ARMY_BASE_UPKEEP);
}

function buildLoanLines(loans: LoanState[]): EconomyLedgerLine[] {
  if (loans.length === 0) {
    return [];
  }
  const payment = Math.round(loans[0].principal * 0.1);
  return [{ label: "Loan Interest", amount: -payment, category: "loan" }];
}

export function buildEconomyLines(
  _prev: CampaignWorldView | null,
  next: CampaignWorldView,
): EconomyLedgerLine[] {
  const taxIncome = calculateTaxIncome(next);
  const armyUpkeep = calculateArmyUpkeep(next);
  const taxRate = next.my_faction.tax_rate;

  return [
    {
      label: "Provincial Taxes",
      amount: taxIncome,
      category: "tax",
      details: `${taxRate} taxation across realm`,
    },
    {
      label: "Military Upkeep",
      amount: -armyUpkeep,
      category: "upkeep",
      details: "Standing army provisions and pay",
    },
    ...buildLoanLines(next.my_faction.loans),
  ];
}

function buildSingleBattleReport(
  battle: BattleView,
  regionNames: Record<string, string>,
): BattleReportItem {
  const regionName = regionNames[battle.region_id] ?? battle.region_id;
  const outcome = mapBattleOutcome(battle.outcome);
  const rounds = buildTacticalRounds(battle.exchanges_used, outcome);
  const varnLosses = rounds.reduce((sum, r) => sum + (r.varnCasualties ?? 0), 0);
  const rivalLosses = rounds.reduce((sum, r) => sum + (r.rivalCasualties ?? 0), 0);
  const isVictory = outcome.includes("victory");
  const summary = isVictory
    ? `Forces engaged and secured the field at ${regionName}.`
    : `Clashed with hostile army at ${regionName}.`;

  return {
    id: battle.id,
    name: `Battle of ${regionName}`,
    regionId: battle.region_id,
    regionName,
    outcome,
    summary,
    rounds,
    varnLosses,
    rivalLosses,
    warScoreDelta: getWarScoreDelta(outcome),
  };
}

export function buildBattleReports(
  battles: BattleView[],
  regionNames: Record<string, string>,
): BattleReportItem[] {
  return battles.map((battle) =>
    buildSingleBattleReport(battle, regionNames),
  );
}

function createUnrestDispatch(
  region: RegionView,
  regionNames: Record<string, string>,
): ReportItem {
  const regionName = regionNames[region.region_id] ?? region.region_id;
  const unrest = region.detail?.unrest ?? 0;
  return {
    id: `dispatch-unrest-${region.region_id}`,
    category: "internal",
    title: `${regionName} Discontent`,
    description: "Murmurs of discontent spread among the local populace and garrison.",
    badge: { label: "Restless", tone: "warning" },
    signedValue: `+${unrest}%`,
    regionId: region.region_id,
  };
}

function buildUnrestDispatches(
  regions: RegionView[],
  myFactionId: string,
  regionNames: Record<string, string>,
): ReportItem[] {
  const owned = regions.filter(
    (region) =>
      region.owner_id === myFactionId ||
      region.detail?.owner_id === myFactionId,
  );
  return owned
    .filter((region) => (region.detail?.unrest ?? 0) >= HIGH_UNREST_THRESHOLD)
    .map((region) => createUnrestDispatch(region, regionNames));
}

function buildInternalDispatches(
  prev: CampaignWorldView | null,
  next: CampaignWorldView,
  regionNames: Record<string, string>,
): ReportItem[] {
  const items = buildUnrestDispatches(
    next.regions,
    next.my_faction.id,
    regionNames,
  );

  if (prev && next.my_faction.stability < prev.my_faction.stability) {
    const delta = next.my_faction.stability - prev.my_faction.stability;
    items.push({
      id: "dispatch-stability-drop",
      category: "internal",
      title: "Realm Stability Declines",
      description: "Recent developments have unsettled the lords and courts.",
      badge: { label: "Unstable", tone: "danger" },
      signedValue: `${delta}%`,
    });
  }

  return items;
}

function buildDiplomacyDispatches(next: CampaignWorldView): ReportItem[] {
  const items: ReportItem[] = [];

  for (const rival of next.rivals as RivalView[]) {
    if (rival.relation === "war") {
      items.push({
        id: `dispatch-rival-${rival.faction_id}`,
        category: "diplomacy",
        title: `${rival.name} Mobilization`,
        description: `Hostilities continue with ${rival.leader_name ?? rival.name}.`,
        badge: { label: "At War", tone: "danger" },
      });
    } else if (rival.relation === "alliance") {
      items.push({
        id: `dispatch-rival-${rival.faction_id}`,
        category: "diplomacy",
        title: `${rival.name} Pact`,
        description: `Envoys from ${rival.leader_name ?? rival.name} confirm our mutual treaty.`,
        badge: { label: "Allied", tone: "positive" },
      });
    }
  }

  return items;
}

function buildMilitaryDispatches(
  battles: BattleReportItem[],
): ReportItem[] {
  return battles.map((battle) => {
    const isVictory = battle.outcome.includes("victory");
    return {
      id: `dispatch-battle-${battle.id}`,
      category: "military",
      title: `Engagement at ${battle.regionName}`,
      description: battle.summary,
      badge: {
        label: isVictory ? "Victory" : "Defeat",
        tone: isVictory ? "positive" : "danger",
      },
      regionId: battle.regionId,
    };
  });
}

export function buildDispatches(
  prev: CampaignWorldView | null,
  next: CampaignWorldView,
  regionNames: Record<string, string>,
  battles: BattleReportItem[] = [],
): ReportItem[] {
  const internal = buildInternalDispatches(prev, next, regionNames);
  const diplomacy = buildDiplomacyDispatches(next);
  const military = buildMilitaryDispatches(battles);
  return [...internal, ...diplomacy, ...military];
}

function getLeadBattleHeadline(leadBattle: BattleReportItem): string {
  if (leadBattle.outcome.includes("victory")) {
    return `${leadBattle.regionName} held`;
  }
  return `Clash at ${leadBattle.regionName}`;
}

export function deriveHeadline(
  battles: BattleReportItem[],
  stats: TurnReportQuickStats,
): string {
  if (battles.length > 0) {
    return getLeadBattleHeadline(battles[0]);
  }
  if (stats.stabilityDelta < -3) {
    return "Unrest shakes the realm";
  }
  if (stats.netGold < -30) {
    return "Treasury strained by military upkeep";
  }
  return "Seasonal Ledger & Realm Dispatches";
}

export function deriveTurnReport(
  prevWorld: CampaignWorldView | null,
  nextWorld: CampaignWorldView,
  regionNames: Record<string, string>,
): StrategyTurnReportData {
  const date = deriveDate(nextWorld.clock);
  const quickStats = calculateQuickStats(prevWorld, nextWorld);
  const battles = buildBattleReports(nextWorld.battles, regionNames);
  const economyLines = buildEconomyLines(prevWorld, nextWorld);
  const items = buildDispatches(prevWorld, nextWorld, regionNames, battles);
  const headline = deriveHeadline(battles, quickStats);

  return {
    turn: nextWorld.turn,
    seasonTitle: `${date.season}, Year ${date.year}`,
    headline,
    quickStats,
    battles,
    economyLines,
    items,
    estimatedSections: ALL_ESTIMATED_SECTIONS,
  };
}
