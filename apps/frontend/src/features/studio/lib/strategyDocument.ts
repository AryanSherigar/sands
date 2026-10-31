import {
  AMBITION_PRESETS,
  DEFAULT_AMBITION_PRESET_ID,
  DEFAULT_FACTION_MANPOWER,
  DEFAULT_FACTION_STABILITY,
  DEFAULT_FACTION_TREASURY,
  DEFAULT_LEADER_AGE,
  DEFAULT_LEADER_TRAIT_IDS,
  DEFAULT_START_MONTH,
  DEFAULT_START_YEAR,
  FACTION_COLORS,
  STUDIO_DEFAULT_END_YEAR,
} from "../constants/strategyAuthoring";
import type {
  StrategyAmbition,
  StrategyArmy,
  StrategyClaim,
  StrategyCommander,
  StrategyFaction,
  StrategyFields,
  StrategyGrudge,
  StrategyLeader,
  StrategyRegionSetup,
  StrategyRelation,
  StrategyTiming,
} from "../types/strategyDocument.types";
import { makeUniqueId } from "./strategyIds";
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
  };
};

export const applyStrategyFields = (raw: RawDocument, fields: StrategyFields): RawDocument => ({
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
  tuning: { ...((raw.tuning ?? {}) as RawDocument), ...fields.timing },
});

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
