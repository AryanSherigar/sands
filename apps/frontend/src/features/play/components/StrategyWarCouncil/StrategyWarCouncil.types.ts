export type TerrainType = "plains" | "forest" | "hills" | "mountain" | "marsh" | "desert" | "river";
export type WeatherType = "clear" | "rain" | "severe";
export type FormationType = "balanced" | "defensive" | "concentrated";
export type TacticType = "hold" | "press" | "flank" | "hold_high_ground" | "feigned_retreat" | "forest_flank" | "night_attack";
export type WithdrawalPolicyType = "preserve" | "balanced" | "hold_at_cost";
export type ReservePolicyType = "conserve" | "reinforce_on_pressure";
export type SupplyType = "supplied" | "strained" | "isolated";
export type BattleStatusType = "awaiting_commands" | "awaiting_next_turn" | "resolved";

export interface StandingPlan {
  formation: FormationType;
  tactic: TacticType;
  withdrawal_policy: WithdrawalPolicyType;
  reserve_policy: ReservePolicyType;
}

export interface ContingentView {
  faction_id: string;
  army_ids: string[];
  troops: Record<string, number>;
  morale: number;
  fatigue: number;
  plan: StandingPlan;
  supply: SupplyType;
  status: string;
}

export interface StrengthInterval {
  minimum: number;
  maximum: number;
  exact?: number;
}

export type MissionTarget = "composition" | "reserves" | "preparation";
export type ReconConfidence = "low" | "medium" | "high";
export type PreparationHint = "holding" | "advancing" | "flanking" | "withdrawing";

export interface ReconReport {
  id: string;
  battle_id: string;
  observer_faction_id: string;
  subject_faction_id: string;
  mission_id: string;
  target: MissionTarget;
  observed_turn: number;
  observed_exchange: number;
  available_from_wave: number;
  strength: StrengthInterval;
  composition?: Record<string, number> | null;
  reserves?: StrengthInterval | null;
  preparation_hint?: PreparationHint | null;
  confidence: ReconConfidence;
}

export interface OpponentView {
  faction_id: string;
  strength: StrengthInterval;
  reports: ReconReport[];
}

export interface BattleView {
  id: string;
  region_id: string;
  status: BattleStatusType;
  outcome: string | null;
  current_turn: number;
  exchanges_used: number;
  total_exchanges: number;
  is_big: boolean;
  control_mode: string;
  terrain: TerrainType;
  weather: WeatherType;
  command_cost: number;
  frontage?: number;
  own_contingent?: ContingentView;
  opponents: OpponentView[];
  legal_commands: string[];
}

export interface ExchangeReport {
  battle_id: string;
  campaign_turn: number;
  exchange_index: number;
  total_exchange: number;
  own_losses: Record<string, number>;
  opponent_strength: StrengthInterval;
  outcome: string | null;
  observations?: ReconReport[];
}

export interface TacticalFactor {
  id: string;
  name: string;
  icon: string;
  valuePercent: number;
  isPositive: boolean;
  title: string;
  explanation: string;
}

export interface TacticalOddsEstimate {
  balancePercent: number;
  isRange: boolean;
  minPercent: number;
  maxPercent: number;
  tierText: string;
  factors: TacticalFactor[];
  playerLossEstimated: number;
  enemyLossEstimated: number;
  warScoreEstimated: number;
}

export type TroopClassification = "infantry" | "cavalry" | "archers_siege";
export type RankTier = "front" | "middle" | "rear";
export type WardIdentifier = "left" | "center" | "right";
export type WardStance = "hold" | "advance" | "refuse";

export interface WardRankCohort {
  id: string;
  troopType: TroopClassification;
  name: string;
  count: number;
  rankOrder: RankTier;
  tacticalRole: string;
}

export interface WardConfig {
  ward: WardIdentifier;
  title: string;
  stance: WardStance;
  isAnchor: boolean;
  ranks: WardRankCohort[];
}

export interface HistoricalDoctrine {
  id: TacticType;
  name: string;
  latinName?: string;
  summary: string;
  risk: string;
  requiredTerrain?: TerrainType[];
  requiredTroopRatio?: {
    troopType: TroopClassification;
    minRatio: number;
    label: string;
  };
}

export interface NobleCaptive {
  nobleId: string;
  name: string;
  title: string;
  factionId: string;
  ransomValueGold: number;
}
