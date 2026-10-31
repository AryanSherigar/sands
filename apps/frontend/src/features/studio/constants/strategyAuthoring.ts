export const STRATEGY_SCENARIO_TITLE = "Untitled strategy scenario";
export const STRATEGY_ID_MAX_LENGTH = 40;
export const STRATEGY_ID_SLUG_LENGTH = 30;
export const STRATEGY_ID_FALLBACK_PREFIX = "f_";
export const STRATEGY_SAVE_DEBOUNCE_MS = 800;
export const MIN_FACTIONS_TO_PUBLISH = 2;

export const DEFAULT_LEADER_AGE = 40;
export const DEFAULT_FACTION_TREASURY = 100;
export const DEFAULT_FACTION_MANPOWER = 400;
export const DEFAULT_FACTION_STABILITY = 60;
export const DEFAULT_LEADER_TRAIT_IDS: readonly string[] = ["pragmatic", "cautious"];
export const DEFAULT_REGION_POPULATION = 900;
export const DEFAULT_REGION_WEALTH = 50;
export const DEFAULT_REGION_MANPOWER = 100;
export const DEFAULT_REGION_GARRISON = 50;
export const DEFAULT_REGION_UNREST = 10;
export const DEFAULT_ARMY_TROOPS = { infantry: 250 } as const;
export const DEFAULT_ARMY_MORALE = 70;
export const DEFAULT_VASSAL_TRIBUTE_PERCENT = 20;
export const DEFAULT_GRUDGE_OPINION = -50;
export const MAX_GRUDGE_REASON_CHARS = 2000;
export const MAX_PERCENT = 100;
export const MAX_COMMANDER_TRAITS = 2;
export const MIN_OPINION = -100;
export const MAX_OPINION = 100;
export const DEFAULT_START_YEAR = 1000;
export const DEFAULT_START_MONTH = 3;
export const STUDIO_DEFAULT_END_YEAR = 1004;
export const MONTHS_PER_YEAR = 12;
export const MONTHS_PER_TURN = 2;
export const TROOP_TYPE_OPTIONS: readonly { id: "infantry" | "cavalry" | "archers_siege"; name: string }[] = [
  { id: "infantry", name: "Infantry" },
  { id: "cavalry", name: "Cavalry" },
  { id: "archers_siege", name: "Archers & siege" },
];
export const RELATION_STATUS_OPTIONS: readonly { value: "war" | "peace" | "alliance"; label: string }[] = [
  { value: "peace", label: "Peace" },
  { value: "war", label: "War" },
  { value: "alliance", label: "Alliance" },
];
export const NO_OVERLORD = "";
export type StartPresetId = "peaceful" | "border_war";
export const START_PRESETS: readonly { id: StartPresetId; label: string; description: string }[] = [
  { id: "peaceful", label: "Peaceful start", description: "Everyone at peace, one army per faction in its capital." },
  { id: "border_war", label: "Border war", description: "The first two factions at war with armies on their shared border." },
];
export const DEFAULT_AMBITION_PRESET_ID = "expand";

export const FACTION_COLORS: readonly string[] = [
  "#8b2e2e",
  "#2e5a8b",
  "#3d7a3d",
  "#8b6b2e",
  "#6b2e8b",
  "#2e8b7a",
  "#8b2e5a",
  "#5a5a5a",
];

export interface TraitOption {
  id: string;
  name: string;
}

// Mirrors BUILTIN_TRAITS in packages/strategy-contracts/strategy_contracts/traits.py.
export const BUILTIN_TRAIT_OPTIONS: readonly TraitOption[] = [
  { id: "honorable", name: "Honorable" },
  { id: "treacherous", name: "Treacherous" },
  { id: "proud", name: "Proud" },
  { id: "wrathful", name: "Wrathful" },
  { id: "cautious", name: "Cautious" },
  { id: "pragmatic", name: "Pragmatic" },
  { id: "cunning", name: "Cunning" },
  { id: "paranoid", name: "Paranoid" },
  { id: "trusting", name: "Trusting" },
  { id: "naive", name: "Naive" },
  { id: "stubborn", name: "Stubborn" },
  { id: "calculating", name: "Calculating" },
  { id: "cruel", name: "Cruel" },
  { id: "zealot", name: "Zealot" },
];

export interface AmbitionPreset {
  id: string;
  name: string;
  metric: string;
  operator: string;
  value: number;
}

export const AMBITION_PRESETS: readonly AmbitionPreset[] = [
  { id: "expand", name: "Expand the realm", metric: "region_count", operator: "gte", value: 4 },
  { id: "stable", name: "A stable peace", metric: "stability", operator: "gte", value: 80 },
  { id: "rich", name: "A full treasury", metric: "treasury", operator: "gte", value: 500 },
];
