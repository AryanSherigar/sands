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

export interface StrategyRegionSetup {
  region_id: string;
  owner_id: string | null;
}

export interface StrategyFields {
  factions: StrategyFaction[];
  leaders: StrategyLeader[];
  ambitions: StrategyAmbition[];
  regions: StrategyRegionSetup[];
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
