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
