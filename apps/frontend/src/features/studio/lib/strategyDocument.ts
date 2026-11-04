import {
  AMBITION_PRESETS,
  DEFAULT_AMBITION_PRESET_ID,
  DEFAULT_ENDING_TOGGLES,
  DEFAULT_EVENT_FREQUENCY_PERCENT,
  DEFAULT_FACTION_MANPOWER,
  DEFAULT_FACTION_STABILITY,
  DEFAULT_FACTION_TREASURY,
  DEFAULT_LEADER_AGE,
  DEFAULT_LEADER_TRAIT_IDS,
  DEFAULT_ORDERS_PER_TURN,
  DEFAULT_START_MONTH,
  DEFAULT_START_YEAR,
  DEFAULT_STRATEGY_TOGGLES,
  FACTION_COLORS,
  STUDIO_DEFAULT_END_YEAR,
} from "../constants/strategyAuthoring";
import type {
  StrategyAmbition,
  StrategyArmy,
  StrategyClaim,
  StrategyCommander,
  StrategyEnding,
  StrategyEndingToggles,
  StrategyFaction,
  StrategyFields,
  StrategyGrudge,
  StrategyLeader,
  StrategyRegionSetup,
  StrategyRelation,
  StrategySystemToggles,
  StrategyTiming,
} from "../types/strategyDocument.types";
import { makeUniqueId } from "./strategyIds";
import { applyRules, readRules } from "./strategyRules";
import { addArmy, addPeaceWithAll, withEconomyDefaults } from "./strategyStart";

export { makeUniqueId };

type RawDocument = Record<string, unknown>;

const ZERO_ECONOMY = { population: 0, wealth: 0, manpower: 0, unrest: 0, garrison: 0 };

const asArray = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

const readTiming = (raw: RawDocument): StrategyTiming => {
  const tuning = (raw.tuning ?? {}) as Partial<StrategyTiming>;
  return {
    start_year: tuning.start_year ?? DEFAULT_START_YEAR,
    start_month: tuning.start_month ?? DEFAULT_START_MONTH,
    end_year: tuning.end_year ?? STUDIO_DEFAULT_END_YEAR,
  };
};

const readToggles = (raw: RawDocument): StrategySystemToggles => {
  const toggles = (raw.toggles ?? {}) as Partial<StrategySystemToggles>;
  return {
    is_loans_enabled: toggles.is_loans_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_loans_enabled,
    is_events_enabled: toggles.is_events_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_events_enabled,
    is_outrage_enabled: toggles.is_outrage_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_outrage_enabled,
    is_overtures_enabled: toggles.is_overtures_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_overtures_enabled,
    is_ai_peace_enabled: toggles.is_ai_peace_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_ai_peace_enabled,
    is_ai_pressure_enabled: toggles.is_ai_pressure_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_ai_pressure_enabled,
    is_ai_subsidy_enabled: toggles.is_ai_subsidy_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_ai_subsidy_enabled,
    is_ai_vassal_enabled: toggles.is_ai_vassal_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_ai_vassal_enabled,
    is_ai_alliance_enabled: toggles.is_ai_alliance_enabled ?? DEFAULT_STRATEGY_TOGGLES.is_ai_alliance_enabled,
  };
};

const readEndingToggles = (raw: RawDocument): StrategyEndingToggles => {
  const tuning = (raw.tuning ?? {}) as RawDocument;
  const endingsBlock = (tuning.endings ?? {}) as RawDocument;
  const toggles = (endingsBlock.toggles ?? {}) as Partial<StrategyEndingToggles>;
  return {
    is_regime_fall_enabled: toggles.is_regime_fall_enabled ?? DEFAULT_ENDING_TOGGLES.is_regime_fall_enabled,
    is_hegemony_enabled: toggles.is_hegemony_enabled ?? DEFAULT_ENDING_TOGGLES.is_hegemony_enabled,
    is_negotiated_end_enabled: toggles.is_negotiated_end_enabled ?? DEFAULT_ENDING_TOGGLES.is_negotiated_end_enabled,
    is_end_date_enabled: toggles.is_end_date_enabled ?? DEFAULT_ENDING_TOGGLES.is_end_date_enabled,
    is_vassal_outcome_enabled: toggles.is_vassal_outcome_enabled ?? DEFAULT_ENDING_TOGGLES.is_vassal_outcome_enabled,
  };
};

const readOrdersPerTurn = (raw: RawDocument): number => {
  const tuning = (raw.tuning ?? {}) as RawDocument;
  return typeof tuning.orders_per_turn === "number" ? tuning.orders_per_turn : DEFAULT_ORDERS_PER_TURN;
};

const readEventFrequency = (raw: RawDocument): number => {
  const tuning = (raw.tuning ?? {}) as RawDocument;
  return typeof tuning.event_frequency_percent === "number"
    ? tuning.event_frequency_percent
    : DEFAULT_EVENT_FREQUENCY_PERCENT;
};

// NOTE: the server validates the full document; this only reads the slices Studio edits.
export const readStrategyFields = (raw: RawDocument): StrategyFields => {
  const starting = (raw.starting ?? {}) as Record<string, unknown>;
  return {
    factions: asArray<StrategyFaction>(raw.factions),
    leaders: asArray<StrategyLeader>(raw.leaders),
    ambitions: asArray<StrategyAmbition>(raw.ambitions),
    regions: asArray<StrategyRegionSetup>(starting.regions).map((item) => ({ ...ZERO_ECONOMY, ...item })),
    armies: asArray<StrategyArmy>(starting.armies),
    commanders: asArray<StrategyCommander>(raw.commanders),
    relations: asArray<StrategyRelation>(starting.relations),
    claims: asArray<StrategyClaim>(starting.claims),
    grudges: asArray<StrategyGrudge>(starting.grudges),
    timing: readTiming(raw),
    rules: readRules((raw.tuning ?? {}) as RawDocument),
    toggles: readToggles(raw),
    is_using_default_endings: raw.is_using_default_endings !== false,
    endings: asArray<StrategyEnding>(raw.endings),
    ending_toggles: readEndingToggles(raw),
    disabled_builtin_event_ids: asArray<string>(raw.disabled_builtin_event_ids),
    orders_per_turn: readOrdersPerTurn(raw),
    event_frequency_percent: readEventFrequency(raw),
  };
};

const hasDiff = (a: Record<string, unknown>, b: Record<string, unknown>): boolean => {
  const keys = Object.keys(b);
  return keys.some((key) => a[key] !== b[key]);
};

export const applyStrategyFields = (raw: RawDocument, fields: StrategyFields): RawDocument => {
  const rawTuning = (raw.tuning ?? {}) as RawDocument;
  const rawEndings = (rawTuning.endings ?? {}) as RawDocument;
  const rawEndingToggles = (rawEndings.toggles ?? {}) as RawDocument;

  const nextTuning: RawDocument = {
    ...rawTuning,
    ...fields.timing,
  };

  if (rawTuning.orders_per_turn !== undefined || fields.orders_per_turn !== DEFAULT_ORDERS_PER_TURN) {
    nextTuning.orders_per_turn = fields.orders_per_turn;
  }
  if (rawTuning.event_frequency_percent !== undefined || fields.event_frequency_percent !== DEFAULT_EVENT_FREQUENCY_PERCENT) {
    nextTuning.event_frequency_percent = fields.event_frequency_percent;
  }
  if (rawTuning.endings !== undefined || hasDiff(fields.ending_toggles as unknown as Record<string, unknown>, DEFAULT_ENDING_TOGGLES as unknown as Record<string, unknown>)) {
    nextTuning.endings = {
      ...rawEndings,
      toggles: {
        ...rawEndingToggles,
        ...fields.ending_toggles,
      },
    };
  }

  const result: RawDocument = {
    ...raw,
    factions: fields.factions,
    leaders: fields.leaders,
    ambitions: fields.ambitions,
    commanders: fields.commanders,
    starting: {
      ...((raw.starting ?? {}) as RawDocument),
      regions: fields.regions,
      armies: fields.armies,
      relations: fields.relations,
      claims: fields.claims,
      grudges: fields.grudges,
    },
    tuning: applyRules(nextTuning, fields.rules),
  };

  if (raw.toggles !== undefined || hasDiff(fields.toggles as unknown as Record<string, unknown>, DEFAULT_STRATEGY_TOGGLES as unknown as Record<string, unknown>)) {
    result.toggles = {
      ...((raw.toggles ?? {}) as RawDocument),
      ...fields.toggles,
    };
  }
  if (raw.is_using_default_endings !== undefined || !fields.is_using_default_endings) {
    result.is_using_default_endings = fields.is_using_default_endings;
  }
  if (raw.endings !== undefined || fields.endings.length > 0) {
    result.endings = fields.endings;
  }
  if (raw.disabled_builtin_event_ids !== undefined || fields.disabled_builtin_event_ids.length > 0) {
    result.disabled_builtin_event_ids = fields.disabled_builtin_event_ids;
  }

  return result;
};

const buildAmbition = (presetId: string, factionId: string): StrategyAmbition => {
  const preset = AMBITION_PRESETS.find((item) => item.id === presetId) ?? AMBITION_PRESETS[0];
  return {
    id: `${factionId}_${preset.id}`,
    name: preset.name,
    condition: {
      kind: "comparison",
      metric: preset.metric,
      subject_id: factionId,
      operator: preset.operator,
      value: preset.value,
    },
  };
};

export const addFaction = (fields: StrategyFields, name: string): StrategyFields => {
  const takenIds = [...fields.factions.map((item) => item.id), ...fields.leaders.map((item) => item.id)];
  const factionId = makeUniqueId(name, takenIds);
  const leaderId = makeUniqueId(`${factionId}_ruler`, [...takenIds, factionId]);
  const ambition = buildAmbition(DEFAULT_AMBITION_PRESET_ID, factionId);
  const faction: StrategyFaction = {
    id: factionId,
    name,
    color: FACTION_COLORS[fields.factions.length % FACTION_COLORS.length],
    capital_region_id: null,
    leader_id: leaderId,
    treasury: DEFAULT_FACTION_TREASURY,
    manpower: DEFAULT_FACTION_MANPOWER,
    stability: DEFAULT_FACTION_STABILITY,
    is_playable: fields.factions.length === 0,
  };
  const leader: StrategyLeader = {
    id: leaderId,
    name: `Ruler of ${name}`,
    faction_id: factionId,
    trait_ids: [...DEFAULT_LEADER_TRAIT_IDS],
    ambition_ids: [ambition.id],
    history: "",
    age: DEFAULT_LEADER_AGE,
  };
  return addPeaceWithAll(
    {
      ...fields,
      factions: [...fields.factions, faction],
      leaders: [...fields.leaders, leader],
      ambitions: [...fields.ambitions, ambition],
    },
    factionId,
  );
};

export const removeFaction = (fields: StrategyFields, factionId: string): StrategyFields => {
  const leaderIds = fields.leaders.filter((item) => item.faction_id === factionId).map((item) => item.id);
  return {
    ...fields,
    factions: fields.factions.filter((item) => item.id !== factionId),
    leaders: fields.leaders.filter((item) => item.faction_id !== factionId),
    ambitions: fields.ambitions.filter((item) => item.condition.subject_id !== factionId),
    regions: fields.regions.map((item) => (item.owner_id === factionId ? { ...item, owner_id: null } : item)),
    armies: fields.armies.filter((item) => item.owner_id !== factionId),
    commanders: fields.commanders.filter((item) => item.faction_id !== factionId),
    relations: fields.relations.filter((item) => item.faction_a !== factionId && item.faction_b !== factionId),
    claims: fields.claims.filter((item) => item.faction_id !== factionId),
    grudges: fields.grudges.filter(
      (item) => !leaderIds.includes(item.holder_id) && !leaderIds.includes(item.target_id),
    ),
  };
};

export const updateFaction = (
  fields: StrategyFields,
  factionId: string,
  patch: Partial<StrategyFaction>,
): StrategyFields => ({
  ...fields,
  factions: fields.factions.map((item) => (item.id === factionId ? { ...item, ...patch } : item)),
});

export const updateLeader = (
  fields: StrategyFields,
  leaderId: string,
  patch: Partial<StrategyLeader>,
): StrategyFields => ({
  ...fields,
  leaders: fields.leaders.map((item) => (item.id === leaderId ? { ...item, ...patch } : item)),
});

export const setLeaderAmbitionPreset = (
  fields: StrategyFields,
  leaderId: string,
  presetId: string,
): StrategyFields => {
  const leader = fields.leaders.find((item) => item.id === leaderId);
  if (!leader) return fields;
  const ambition = buildAmbition(presetId, leader.faction_id);
  const keptAmbitions = fields.ambitions.filter((item) => !leader.ambition_ids.includes(item.id));
  const withAmbition = { ...fields, ambitions: [...keptAmbitions, ambition] };
  return updateLeader(withAmbition, leaderId, { ambition_ids: [ambition.id] });
};

export const getAmbitionPresetId = (fields: StrategyFields, leader: StrategyLeader): string => {
  const ambition = fields.ambitions.find((item) => item.id === leader.ambition_ids[0]);
  const preset = AMBITION_PRESETS.find((item) => ambition?.id === `${leader.faction_id}_${item.id}`);
  return preset?.id ?? "";
};

const withOwnedRegion = (fields: StrategyFields, regionId: string, ownerId: string): StrategyFields => {
  const owned = fields.regions.map((item) => (item.region_id === regionId ? withEconomyDefaults(item) : item));
  const hasArmy = fields.armies.some((item) => item.owner_id === ownerId);
  const seeded = { ...fields, regions: owned };
  return hasArmy ? seeded : addArmy(seeded, ownerId, regionId);
};

export const setRegionOwner = (
  fields: StrategyFields,
  regionId: string,
  ownerId: string | null,
): StrategyFields => {
  const isKnown = fields.regions.some((item) => item.region_id === regionId);
  const regions = isKnown
    ? fields.regions.map((item) => (item.region_id === regionId ? { ...item, owner_id: ownerId } : item))
    : [...fields.regions, { ...ZERO_ECONOMY, region_id: regionId, owner_id: ownerId }];
  const updated = { ...fields, regions };
  return ownerId === null ? updated : withOwnedRegion(updated, regionId, ownerId);
};

export const getRegionOwner = (fields: StrategyFields, regionId: string): string | null =>
  fields.regions.find((item) => item.region_id === regionId)?.owner_id ?? null;
