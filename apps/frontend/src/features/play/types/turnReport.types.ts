export type TurnReportCategory =
  | "all"
  | "military"
  | "economy"
  | "diplomacy"
  | "internal";

export interface TacticalRound {
  round: number;
  description: string;
  varnCasualties?: number;
  rivalCasualties?: number;
  outcomeNote?: string;
}

export type BattleOutcome =
  | "decisive_victory"
  | "marginal_victory"
  | "defeat"
  | "stalemate";

export interface BattleReportItem {
  id: string;
  name: string;
  regionId: string;
  regionName: string;
  outcome: BattleOutcome;
  summary: string;
  rounds: TacticalRound[];
  varnLosses: number;
  rivalLosses: number;
  warScoreDelta: number;
}

export interface EconomyLedgerLine {
  label: string;
  amount: number;
  category: "tax" | "upkeep" | "repair" | "loan" | "other";
  details?: string;
}

export type ItemTone = "positive" | "warning" | "neutral" | "danger";

export interface ReportItem {
  id: string;
  category: Exclude<TurnReportCategory, "all">;
  title: string;
  description: string;
  badge?: {
    label: string;
    tone: ItemTone;
  };
  signedValue?: string;
  regionId?: string;
}

export interface TurnReportQuickStats {
  netGold: number;
  totalCasualties: number;
  stability: number;
  stabilityDelta: number;
  manpower: number;
}

export type EstimatedSection =
  | "economy_lines"
  | "casualties"
  | "battle_results"
  | "event_dispatches"
  | "stability_delta"
  | "war_score"
  | "rival_casualties"
  | "tactical_round_text"
  | "diplomacy_dispatches"
  | "victory_margin";

export interface StrategyTurnReportData {
  turn: number;
  seasonTitle: string;
  headline: string;
  quickStats: TurnReportQuickStats;
  battles: BattleReportItem[];
  economyLines: EconomyLedgerLine[];
  items: ReportItem[];
  /** Sections still filled by frontend estimates; see TURN_REPORT_GAPS. */
  estimatedSections?: EstimatedSection[];
}
