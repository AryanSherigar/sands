import type { MapDocument } from "@/shared/types/strategy-map.types";

export interface StrategyFaction {
  id: string;
  name: string;
  color: string;
  capital_region_id: string | null;
  leader_id: string | null;
  treasury: number;
  manpower: number;
  stability: number;
  is_playable: boolean;
  stance_ids?: string[] | null;
}

export interface StrategyHeir {
  id: string;
  name: string;
  age: number;
  trait_ids: string[];
}

export interface StrategyLeader {
  id: string;
  name: string;
  faction_id: string;
  trait_ids: string[];
  ambition_ids: string[];
  history: string;
  age: number;
  portrait_url?: string | null;
  avatar_url?: string | null;
  heir?: StrategyHeir | null;
}

export interface StrategyAmbition {
  id: string;
  name: string;
  condition: {
    kind: "comparison";
    metric: string;
    subject_id: string | null;
    operator: string;
    value: number;
  };
}

export type TroopType = "infantry" | "cavalry" | "archers_siege";
export type RelationStatus = "war" | "peace" | "alliance";

export interface StrategyRegionEconomy {
  population: number;
  wealth: number;
  manpower: number;
  unrest: number;
  garrison: number;
}

export interface StrategyRegionSetup extends StrategyRegionEconomy {
  region_id: string;
  owner_id: string | null;
}

export interface StrategyArmy {
  id: string;
  owner_id: string;
  location_id: string;
  troops: Partial<Record<TroopType, number>>;
  commander_id: string | null;
  morale: number;
}

export interface StrategyCommander {
  id: string;
  name: string;
  faction_id: string;
  trait_ids: string[];
  is_important: boolean;
}

export interface StrategyVassalage {
  overlord_id: string;
  tribute_share_percent: number;
  levy_share_percent: number;
  is_foreign_policy_controlled: boolean;
  has_garrison_rights: boolean;
  duration_turns: number;
}

export interface StrategyRelation {
  faction_a: string;
  faction_b: string;
  status: RelationStatus;
  vassalage: StrategyVassalage | null;
}

export interface StrategyClaim {
  faction_id: string;
  region_id: string;
}

export interface StrategyGrudge {
  holder_id: string;
  target_id: string;
  opinion: number;
  reason: string;
}

export interface StrategyTiming {
  start_year: number;
  start_month: number;
  end_year: number;
}

export interface StrategyRules {
  agents_enabled: boolean;
  revolt_talks_enabled: boolean;
  bribe_base_price: number;
  trade_value_per_turn: number;
  trade_income_percent: number;
  access_value_per_turn: number;
  conditional_trigger_percent: number;
  conditional_gate_percent: number;
  oath_offer_min_opinion: number;
  oath_offer_duration_turns: number;
  letters_enabled: boolean;
  letter_cooldown_turns: number;
  judgments_enabled: boolean;
  judgment_cooldown_turns: number;
  judgment_sentence_turns: number;
}

export interface StrategyEnding {
  id: string;
  kind: "victory" | "defeat" | "graded";
  name: string;
  condition: {
    kind: "comparison";
    metric: string;
    subject_id: string | null;
    operator: string;
    value: number;
  };
  epilogue_hint?: string;
}

export interface StrategyEndingToggles {
  is_regime_fall_enabled: boolean;
  is_hegemony_enabled: boolean;
  is_negotiated_end_enabled: boolean;
  is_end_date_enabled: boolean;
  is_vassal_outcome_enabled: boolean;
}

export interface StrategySystemToggles {
  is_loans_enabled: boolean;
  is_events_enabled: boolean;
  is_outrage_enabled: boolean;
  is_overtures_enabled: boolean;
  is_ai_peace_enabled: boolean;
  is_ai_pressure_enabled: boolean;
  is_ai_subsidy_enabled: boolean;
  is_ai_vassal_enabled: boolean;
  is_ai_alliance_enabled: boolean;
}

export interface StrategyFields {
  factions: StrategyFaction[];
  leaders: StrategyLeader[];
  ambitions: StrategyAmbition[];
  regions: StrategyRegionSetup[];
  armies: StrategyArmy[];
  commanders: StrategyCommander[];
  relations: StrategyRelation[];
  claims: StrategyClaim[];
  grudges: StrategyGrudge[];
  timing: StrategyTiming;
  rules: StrategyRules;
  toggles: StrategySystemToggles;
  is_using_default_endings: boolean;
  endings: StrategyEnding[];
  ending_toggles: StrategyEndingToggles;
  disabled_builtin_event_ids: string[];
  orders_per_turn: number;
  event_frequency_percent: number;
}

export interface PublishIssue {
  code: string;
  path: string;
  message: string;
}

export interface PublishReport {
  blocking: PublishIssue[];
  warnings: PublishIssue[];
}

export type StrategyMapState = MapDocument | null;
