import type { MapDocument } from "@/shared/types/strategy-map.types";

export interface StrategyTraitEffect {
  label: string;
  isPositive?: boolean;
}

export interface StrategyTrait {
  id: string;
  name: string;
  description: string;
  effects: StrategyTraitEffect[];
  category?: string;
  icon?: string;
}

export interface StrategyAmbition {
  id: string;
  name: string;
  description: string;
  progress?: number;
  icon?: string;
}

export interface StrategyRulerState {
  name: string;
  epithet: string;
  portraitUrl?: string;
  traitIds: string[];
  ambitionIds: string[];
  backstory: string;
  dynastyName?: string;
  houseMotto?: string;
  houseBadge?: string;
}

export interface FactionCrisisInfo {
  title: string;
  tag?: string;
  description: string;
}

export interface PlayableFactionInfo {
  id: string;
  name: string;
  color: string;
  is_playable?: boolean;
  provinces_count?: number;
  capital_seat?: string;
  government?: string;
  treasury: number;
  manpower: number;
  stability?: number;
  capital_region_id?: string | null;
  leader_id?: string | null;
  role_tag?: string;
  tagline?: string;
  crisis?: FactionCrisisInfo;
}

export interface StrategySetupMapProps {
  mapDoc?: MapDocument | null;
  factions: PlayableFactionInfo[];
  activeFactionId: string;
  onSelectFaction: (factionId: string) => void;
}

export interface StrategyFactionStripProps {
  factions: PlayableFactionInfo[];
  activeFactionId: string;
  onSelectFaction: (factionId: string) => void;
}

export interface StrategyFactionDossierProps {
  faction?: PlayableFactionInfo;
}

export interface StrategyRealmExplorerProps {
  factions: PlayableFactionInfo[];
  activeFactionId: string;
  onSelectFaction: (factionId: string) => void;
  mapDoc?: MapDocument | null;
}
