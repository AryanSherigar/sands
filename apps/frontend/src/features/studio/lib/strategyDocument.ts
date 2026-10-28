import {
  AMBITION_PRESETS,
  DEFAULT_AMBITION_PRESET_ID,
  DEFAULT_FACTION_MANPOWER,
  DEFAULT_FACTION_STABILITY,
  DEFAULT_FACTION_TREASURY,
  DEFAULT_LEADER_AGE,
  DEFAULT_LEADER_TRAIT_IDS,
  FACTION_COLORS,
  STRATEGY_ID_FALLBACK_PREFIX,
  STRATEGY_ID_SLUG_LENGTH,
} from "../constants/strategyAuthoring";
import type {
  StrategyAmbition,
  StrategyFaction,
  StrategyFields,
  StrategyLeader,
  StrategyRegionSetup,
} from "../types/strategyDocument.types";

type RawDocument = Record<string, unknown>;

const asArray = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);

// NOTE: the server validates the full document; this only reads the slices Studio edits.
export const readStrategyFields = (raw: RawDocument): StrategyFields => {
  const starting = (raw.starting ?? {}) as { regions?: unknown };
  return {
    factions: asArray<StrategyFaction>(raw.factions),
    leaders: asArray<StrategyLeader>(raw.leaders),
    ambitions: asArray<StrategyAmbition>(raw.ambitions),
    regions: asArray<StrategyRegionSetup>(starting.regions),
  };
};

export const applyStrategyFields = (raw: RawDocument, fields: StrategyFields): RawDocument => ({
  ...raw,
  factions: fields.factions,
  leaders: fields.leaders,
  ambitions: fields.ambitions,
  starting: { ...((raw.starting ?? {}) as RawDocument), regions: fields.regions },
});

export const makeUniqueId = (name: string, takenIds: readonly string[]): string => {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, STRATEGY_ID_SLUG_LENGTH);
  const base = /^[a-z]/.test(slug) && slug.length >= 2 ? slug : `${STRATEGY_ID_FALLBACK_PREFIX}${slug}`;
  let candidate = base;
  for (let suffix = 2; takenIds.includes(candidate); suffix += 1) {
    candidate = `${base}_${suffix}`;
  }
  return candidate;
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
  return {
    ...fields,
    factions: [...fields.factions, faction],
    leaders: [...fields.leaders, leader],
    ambitions: [...fields.ambitions, ambition],
  };
};

export const removeFaction = (fields: StrategyFields, factionId: string): StrategyFields => ({
  factions: fields.factions.filter((item) => item.id !== factionId),
  leaders: fields.leaders.filter((item) => item.faction_id !== factionId),
  ambitions: fields.ambitions.filter((item) => item.condition.subject_id !== factionId),
  regions: fields.regions.map((item) =>
    item.owner_id === factionId ? { ...item, owner_id: null } : item,
  ),
});

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

export const setRegionOwner = (
  fields: StrategyFields,
  regionId: string,
  ownerId: string | null,
): StrategyFields => {
  const isKnown = fields.regions.some((item) => item.region_id === regionId);
  const regions = isKnown
    ? fields.regions.map((item) => (item.region_id === regionId ? { ...item, owner_id: ownerId } : item))
    : [...fields.regions, { region_id: regionId, owner_id: ownerId }];
  return { ...fields, regions };
};

export const getRegionOwner = (fields: StrategyFields, regionId: string): string | null =>
  fields.regions.find((item) => item.region_id === regionId)?.owner_id ?? null;
