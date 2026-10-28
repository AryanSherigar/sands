import type { TroopType } from "./simulation.types";

export type ApiEconomyCategory = "tax" | "upkeep" | "loan" | "other";
export type ApiBattleSide = "attacker" | "defender";

export interface ApiEconomyLine {
  kind: string;
  category: ApiEconomyCategory;
  amount: number;
  subject_ids: string[];
  inputs: Record<string, number>;
}

export interface ApiBattleRound {
  total_exchange: number;
  own_losses: number;
}

export interface ApiBattleReport {
  battle_id: string;
  region_id: string;
  outcome: string | null;
  own_side: ApiBattleSide;
  exchanges: number;
  own_losses: Partial<Record<TroopType, number>>;
  rounds: ApiBattleRound[];
}

export interface ApiReportCause {
  summary_key: string;
  subject_ids: string[];
  inputs: Record<string, number>;
}

export interface ApiReportLine {
  text_key: string;
  kind: string;
  subject_ids: string[];
  cause?: ApiReportCause;
}

export interface TurnReportResponse {
  turn: number;
  net_gold: number;
  economy: ApiEconomyLine[];
  battles: ApiBattleReport[];
  lines: ApiReportLine[];
  major_event_kinds: string[];
}
