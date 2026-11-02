export interface StrategyWorldSnapshotRegion {
  id: string;
  name?: string;
  owner_faction_id?: string | null;
  terrain?: string;
  unrest?: number;
  manpower?: number;
  is_under_siege?: boolean;
  siege_progress?: number;
}

export interface StrategyWorldSnapshotWar {
  war_id?: string;
  attacker_faction_id?: string;
  defender_faction_id?: string;
  war_score?: number;
}

export interface StrategyWorldSnapshotEvent {
  turn?: number;
  event_type?: string;
  type?: string;
  description?: string;
  [key: string]: unknown;
}

export interface StrategyWorldSnapshotFaction {
  id: string;
  name?: string;
  treasury?: number;
  ruler?: {
    name?: string;
    health_band?: string;
    [key: string]: unknown;
  };
  capital_region_id?: string | null;
  stats?: {
    military?: number;
    economy?: number;
    diplomacy?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface StrategyWorldSnapshot {
  playthrough_id?: string;
  turn?: number;
  season?: string;
  year?: number;
  status?: string;
  orders_remaining?: number;
  my_faction?: StrategyWorldSnapshotFaction;
  regions?: StrategyWorldSnapshotRegion[];
  armies?: unknown[];
  wars?: StrategyWorldSnapshotWar[];
  rivals?: unknown[];
  event_log?: StrategyWorldSnapshotEvent[];
  queued_orders?: unknown[];
  [key: string]: unknown;
}
