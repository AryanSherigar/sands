import {
  DEFAULT_ARMY_MORALE,
  DEFAULT_ARMY_TROOPS,
  DEFAULT_GRUDGE_OPINION,
  DEFAULT_REGION_GARRISON,
  DEFAULT_REGION_MANPOWER,
  DEFAULT_REGION_POPULATION,
  DEFAULT_REGION_UNREST,
  DEFAULT_REGION_WEALTH,
  DEFAULT_VASSAL_TRIBUTE_PERCENT,
  MAX_COMMANDER_TRAITS,
  MAX_GRUDGE_REASON_CHARS,
  MAX_OPINION,
  MAX_PERCENT,
  MIN_OPINION,
  MONTHS_PER_TURN,
  MONTHS_PER_YEAR,
  type StartPresetId,
} from "../constants/strategyAuthoring";
import type { MapRegion } from "@/shared/types/strategy-map.types";
import type {
  RelationStatus,
  StrategyArmy,
  StrategyCommander,
  StrategyFields,
  StrategyGrudge,
  StrategyRegionEconomy,
  StrategyRegionSetup,
  StrategyRelation,
  StrategyTiming,
} from "../types/strategyDocument.types";
import { makeUniqueId } from "./strategyIds";

export const clampWholeNumber = (raw: string | number, max?: number): number => {
  const parsed = Math.floor(Number(raw));
  if (!Number.isFinite(parsed) || parsed < 0) return 0;
  return max === undefined ? parsed : Math.min(parsed, max);
};

const clampOpinion = (raw: number): number =>
  Math.min(MAX_OPINION, Math.max(MIN_OPINION, Math.trunc(Number(raw)) || 0));

export const DEFAULT_REGION_ECONOMY: StrategyRegionEconomy = {
  population: DEFAULT_REGION_POPULATION,
  wealth: DEFAULT_REGION_WEALTH,
  manpower: DEFAULT_REGION_MANPOWER,
  unrest: DEFAULT_REGION_UNREST,
  garrison: DEFAULT_REGION_GARRISON,
};

const EMPTY_ECONOMY: StrategyRegionEconomy = { population: 0, wealth: 0, manpower: 0, unrest: 0, garrison: 0 };

const isEconomyEmpty = (setup: StrategyRegionSetup): boolean =>
  Object.keys(EMPTY_ECONOMY).every((key) => setup[key as keyof StrategyRegionEconomy] === 0);

export const withEconomyDefaults = (setup: StrategyRegionSetup): StrategyRegionSetup =>
  isEconomyEmpty(setup) ? { ...setup, ...DEFAULT_REGION_ECONOMY } : setup;

const clampEconomy = (patch: Partial<StrategyRegionEconomy>): Partial<StrategyRegionEconomy> => {
  const clamped: Partial<StrategyRegionEconomy> = {};
  for (const [key, value] of Object.entries(patch) as [keyof StrategyRegionEconomy, number][]) {
    clamped[key] = clampWholeNumber(value, key === "unrest" ? MAX_PERCENT : undefined);
  }
  return clamped;
};

export const updateRegionEconomy = (
  fields: StrategyFields,
  regionId: string,
  patch: Partial<StrategyRegionEconomy>,
): StrategyFields => {
  const clamped = clampEconomy(patch);
  const isKnown = fields.regions.some((item) => item.region_id === regionId);
  const regions = isKnown
    ? fields.regions.map((item) => (item.region_id === regionId ? { ...item, ...clamped } : item))
    : [...fields.regions, { region_id: regionId, owner_id: null, ...EMPTY_ECONOMY, ...clamped }];
  return { ...fields, regions };
};

export const addArmy = (fields: StrategyFields, factionId: string, locationId: string): StrategyFields => {
  const takenIds = [...fields.armies.map((item) => item.id), ...fields.factions.map((item) => item.id)];
  const army: StrategyArmy = {
    id: makeUniqueId(`${factionId}_army`, takenIds),
    owner_id: factionId,
    location_id: locationId,
    troops: { ...DEFAULT_ARMY_TROOPS },
    commander_id: null,
    morale: DEFAULT_ARMY_MORALE,
  };
  return { ...fields, armies: [...fields.armies, army] };
};

export const updateArmy = (fields: StrategyFields, armyId: string, patch: Partial<StrategyArmy>): StrategyFields => ({
  ...fields,
  armies: fields.armies.map((item) => (item.id === armyId ? { ...item, ...patch } : item)),
});

export const removeArmy = (fields: StrategyFields, armyId: string): StrategyFields => {
  const army = fields.armies.find((item) => item.id === armyId);
  return {
    ...fields,
    armies: fields.armies.filter((item) => item.id !== armyId),
    commanders: fields.commanders.filter((item) => item.id !== army?.commander_id),
  };
};

export type CommanderPatch = Partial<Pick<StrategyCommander, "name" | "trait_ids" | "is_important">>;

const dropCommander = (fields: StrategyFields, army: StrategyArmy): StrategyFields => ({
  ...fields,
  armies: fields.armies.map((item) => (item.id === army.id ? { ...item, commander_id: null } : item)),
  commanders: fields.commanders.filter((item) => item.id !== army.commander_id),
});

const createCommander = (fields: StrategyFields, army: StrategyArmy, patch: CommanderPatch): StrategyFields => {
  const commander: StrategyCommander = {
    id: makeUniqueId(`${army.id}_commander`, fields.commanders.map((item) => item.id)),
    name: (patch.name ?? "").trim(),
    faction_id: army.owner_id,
    trait_ids: patch.trait_ids?.slice(0, MAX_COMMANDER_TRAITS) ?? [],
    is_important: patch.is_important ?? false,
  };
  return {
    ...fields,
    armies: fields.armies.map((item) => (item.id === army.id ? { ...item, commander_id: commander.id } : item)),
    commanders: [...fields.commanders, commander],
  };
};

export const setArmyCommander = (fields: StrategyFields, armyId: string, patch: CommanderPatch): StrategyFields => {
  const army = fields.armies.find((item) => item.id === armyId);
  if (!army) return fields;
  const existing = fields.commanders.find((item) => item.id === army.commander_id);
  if (!existing) return (patch.name ?? "").trim() === "" ? fields : createCommander(fields, army, patch);
  const next = { ...existing, ...patch, name: (patch.name ?? existing.name).trim() };
  if (next.name === "") return dropCommander(fields, army);
  const traitIds = next.trait_ids.slice(0, MAX_COMMANDER_TRAITS);
  return {
    ...fields,
    commanders: fields.commanders.map((item) => (item.id === existing.id ? { ...next, trait_ids: traitIds } : item)),
  };
};

const isSamePair = (relation: StrategyRelation, factionA: string, factionB: string): boolean =>
  (relation.faction_a === factionA && relation.faction_b === factionB) ||
  (relation.faction_a === factionB && relation.faction_b === factionA);

const upsertRelation = (fields: StrategyFields, next: StrategyRelation): StrategyFields => {
  const isKnown = fields.relations.some((item) => isSamePair(item, next.faction_a, next.faction_b));
  const relations = isKnown
    ? fields.relations.map((item) => (isSamePair(item, next.faction_a, next.faction_b) ? next : item))
    : [...fields.relations, next];
  return { ...fields, relations };
};

export const setRelation = (
  fields: StrategyFields,
  factionA: string,
  factionB: string,
  status: RelationStatus,
): StrategyFields => {
  if (factionA === factionB) return fields;
  const existing = fields.relations.find((item) => isSamePair(item, factionA, factionB));
  const vassalage = status === "peace" ? (existing?.vassalage ?? null) : null;
  return upsertRelation(fields, {
    faction_a: existing?.faction_a ?? factionA,
    faction_b: existing?.faction_b ?? factionB,
    status,
    vassalage,
  });
};

export const setVassalage = (
  fields: StrategyFields,
  factionA: string,
  factionB: string,
  overlordId: string | null,
): StrategyFields => {
  const existing = fields.relations.find((item) => isSamePair(item, factionA, factionB));
  if (!existing || existing.status !== "peace") return fields;
  if (overlordId === null) return upsertRelation(fields, { ...existing, vassalage: null });
  if (overlordId !== existing.faction_a && overlordId !== existing.faction_b) return fields;
  const vassalage = existing.vassalage ?? {
    overlord_id: overlordId,
    tribute_share_percent: DEFAULT_VASSAL_TRIBUTE_PERCENT,
    levy_share_percent: 0,
    is_foreign_policy_controlled: false,
    has_garrison_rights: false,
    duration_turns: 0,
  };
  return upsertRelation(fields, { ...existing, vassalage: { ...vassalage, overlord_id: overlordId } });
};

const newPeace = (factionA: string, factionB: string): StrategyRelation => ({
  faction_a: factionA < factionB ? factionA : factionB,
  faction_b: factionA < factionB ? factionB : factionA,
  status: "peace",
  vassalage: null,
});

export const addPeaceWithAll = (fields: StrategyFields, factionId: string): StrategyFields =>
  fields.factions
    .filter((item) => item.id !== factionId)
    .reduce((current, other) => upsertRelation(current, newPeace(factionId, other.id)), fields);

export const addClaim = (fields: StrategyFields, factionId: string, regionId: string): StrategyFields => {
  const isKnown = fields.claims.some((item) => item.faction_id === factionId && item.region_id === regionId);
  if (isKnown) return fields;
  return { ...fields, claims: [...fields.claims, { faction_id: factionId, region_id: regionId }] };
};

export const removeClaim = (fields: StrategyFields, factionId: string, regionId: string): StrategyFields => ({
  ...fields,
  claims: fields.claims.filter((item) => !(item.faction_id === factionId && item.region_id === regionId)),
});

const isSameGrudge = (grudge: StrategyGrudge, holderId: string, targetId: string): boolean =>
  grudge.holder_id === holderId && grudge.target_id === targetId;

export const addGrudge = (fields: StrategyFields, holderId: string, targetId: string): StrategyFields => {
  if (holderId === targetId) return fields;
  if (fields.grudges.some((item) => isSameGrudge(item, holderId, targetId))) return fields;
  const grudge: StrategyGrudge = {
    holder_id: holderId,
    target_id: targetId,
    opinion: DEFAULT_GRUDGE_OPINION,
    reason: "",
  };
  return { ...fields, grudges: [...fields.grudges, grudge] };
};

export const updateGrudge = (
  fields: StrategyFields,
  holderId: string,
  targetId: string,
  patch: Partial<Pick<StrategyGrudge, "opinion" | "reason">>,
): StrategyFields => {
  const safe = {
    ...(patch.opinion === undefined ? {} : { opinion: clampOpinion(patch.opinion) }),
    ...(patch.reason === undefined ? {} : { reason: patch.reason.slice(0, MAX_GRUDGE_REASON_CHARS) }),
  };
  return {
    ...fields,
    grudges: fields.grudges.map((item) => (isSameGrudge(item, holderId, targetId) ? { ...item, ...safe } : item)),
  };
};

export const removeGrudge = (fields: StrategyFields, holderId: string, targetId: string): StrategyFields => ({
  ...fields,
  grudges: fields.grudges.filter((item) => !isSameGrudge(item, holderId, targetId)),
});

export const setTiming = (fields: StrategyFields, patch: Partial<StrategyTiming>): StrategyFields => {
  const merged = { ...fields.timing, ...patch };
  const startMonth = Math.min(MONTHS_PER_YEAR, Math.max(1, Math.trunc(merged.start_month) || 1));
  const endYear = Math.max(merged.end_year, merged.start_year + 1);
  return { ...fields, timing: { start_year: merged.start_year, start_month: startMonth, end_year: endYear } };
};

export const countTurns = (timing: StrategyTiming): number => {
  const monthsUntilEnd = MONTHS_PER_YEAR * (timing.end_year + 1 - timing.start_year) - (timing.start_month - 1);
  return Math.ceil(monthsUntilEnd / MONTHS_PER_TURN);
};

const getOwnedRegionIds = (fields: StrategyFields, factionId: string): string[] =>
  fields.regions.filter((item) => item.owner_id === factionId).map((item) => item.region_id);

const getCapitalOrFirst = (fields: StrategyFields, factionId: string): string | null => {
  const capital = fields.factions.find((item) => item.id === factionId)?.capital_region_id;
  const owned = getOwnedRegionIds(fields, factionId);
  return (capital && owned.includes(capital) ? capital : owned[0]) ?? null;
};

const placeCapitalArmies = (fields: StrategyFields): StrategyFields =>
  fields.factions.reduce((current, faction) => {
    const location = getCapitalOrFirst(current, faction.id);
    return location ? addArmy(current, faction.id, location) : current;
  }, { ...fields, armies: [] as StrategyArmy[], commanders: [] as StrategyCommander[] });

const makeAllPeace = (fields: StrategyFields): StrategyFields =>
  fields.factions.reduce((current, faction) => addPeaceWithAll(current, faction.id), fields);

const getBorderRegion = (
  fields: StrategyFields,
  regions: MapRegion[],
  factionId: string,
  enemyId: string,
): string | null => {
  const enemyIds = getOwnedRegionIds(fields, enemyId);
  const border = regions.find(
    (region) =>
      getOwnedRegionIds(fields, factionId).includes(region.id) &&
      region.neighbor_ids.some((neighborId) => enemyIds.includes(neighborId)),
  );
  return border?.id ?? null;
};

const placeBorderArmy = (fields: StrategyFields, regions: MapRegion[], factionId: string, enemyId: string): StrategyFields => {
  const border = getBorderRegion(fields, regions, factionId, enemyId);
  const isCovered = fields.armies.some((item) => item.owner_id === factionId && item.location_id === border);
  return border && !isCovered ? addArmy(fields, factionId, border) : fields;
};

export const applyPreset = (fields: StrategyFields, presetId: StartPresetId, regions: MapRegion[]): StrategyFields => {
  const peaceful = placeCapitalArmies(makeAllPeace(fields));
  const [first, second] = fields.factions;
  if (presetId === "peaceful" || !first || !second) return peaceful;
  const atWar = setRelation(peaceful, first.id, second.id, "war");
  return placeBorderArmy(placeBorderArmy(atWar, regions, first.id, second.id), regions, second.id, first.id);
};
