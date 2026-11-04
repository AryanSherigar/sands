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
export const DEFAULT_STRATEGY_RULES = {
  agents_enabled: false,
  revolt_talks_enabled: false,
  bribe_base_price: 40,
  trade_value_per_turn: 4,
  trade_income_percent: 10,
  access_value_per_turn: 2,
  conditional_trigger_percent: 60,
  conditional_gate_percent: 100,
  oath_offer_min_opinion: 20,
  oath_offer_duration_turns: 12,
  letters_enabled: false,
  letter_cooldown_turns: 6,
  judgments_enabled: false,
  judgment_cooldown_turns: 6,
  judgment_sentence_turns: 6,
} as const;
export const MAX_CONDITIONAL_PERCENT = 200;
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

export const DEFAULT_ORDERS_PER_TURN = 3;
export const DEFAULT_EVENT_FREQUENCY_PERCENT = 50;
export const DEFAULT_HEIR_AGE = 16;
export const DEFAULT_HEIR_TRAIT_IDS: readonly string[] = ["cautious"];

export const DEFAULT_STRATEGY_TOGGLES = {
  is_loans_enabled: true,
  is_events_enabled: true,
  is_outrage_enabled: true,
  is_overtures_enabled: true,
  is_ai_peace_enabled: true,
  is_ai_pressure_enabled: true,
  is_ai_subsidy_enabled: true,
  is_ai_vassal_enabled: true,
  is_ai_alliance_enabled: true,
} as const;

export const DEFAULT_ENDING_TOGGLES = {
  is_regime_fall_enabled: true,
  is_hegemony_enabled: true,
  is_negotiated_end_enabled: true,
  is_end_date_enabled: true,
  is_vassal_outcome_enabled: true,
} as const;

export const BUILTIN_STANCE_OPTIONS: readonly { id: string; label: string; description: string }[] = [
  { id: "expand", label: "Expand", description: "Aggressive conquest of adjacent regions" },
  { id: "turtle", label: "Turtle", description: "Fortify borders and avoid high-risk wars" },
  { id: "court_ally", label: "Court an ally", description: "Seek pacts and mutual defense" },
  { id: "revenge_on_player", label: "Revenge on player", description: "Focus military spite on player" },
  { id: "rebuild", label: "Rebuild", description: "Prioritize economy and manpower recovery" },
];

export const BUILTIN_DISASTER_OPTIONS: readonly { id: string; label: string; description: string }[] = [
  { id: "tax_grievance", label: "Peasant tax grievance", description: "Unrest from high taxation" },
  { id: "noble_defiance", label: "Noble defiance", description: "Lords defying central authority" },
  { id: "unpaid_mutiny", label: "Army mutiny", description: "Unpaid soldiers rebelling" },
  { id: "realm_in_turmoil", label: "Realm in turmoil", description: "Widespread civil disturbance" },
  { id: "bad_harvest", label: "Bad harvest & famine", description: "Seasonal food shortage and hunger" },
  { id: "plague", label: "Plague & pestilence", description: "Disease outbreak lowering manpower" },
];

export const ENDING_METRIC_OPTIONS: readonly {
  id: string;
  label: string;
  defaultOperator: string;
  defaultValue: number;
}[] = [
  { id: "region_count", label: "Regions controlled", defaultOperator: "gte", defaultValue: 4 },
  { id: "treasury", label: "Gold in treasury", defaultOperator: "gte", defaultValue: 500 },
  { id: "stability", label: "Stability percentage", defaultOperator: "gte", defaultValue: 80 },
  { id: "turn", label: "Turns survived", defaultOperator: "gte", defaultValue: 20 },
  { id: "is_at_peace_with_all", label: "At peace with all realms", defaultOperator: "gte", defaultValue: 1 },
];
