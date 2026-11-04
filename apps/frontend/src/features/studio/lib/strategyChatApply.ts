import type { ActionBlock } from "../types/assistant.types";
import type {
  RelationStatus,
  StrategyFields,
  StrategyRegionEconomy,
  StrategyRules,
  StrategyTiming,
  TroopType,
} from "../types/strategyDocument.types";
import { addFaction, setRegionOwner, updateFaction, updateLeader } from "./strategyDocument";
import { setRules } from "./strategyRules";
import {
  addArmy,
  addClaim,
  addGrudge,
  clampWholeNumber,
  setArmyCommander,
  setRelation,
  setTiming,
  updateArmy,
  updateGrudge,
  updateRegionEconomy,
} from "./strategyStart";

type Payload = Record<string, unknown>;
type BlockResult = StrategyFields | string;

export interface StrategyApplyContext {
  knownRegionIds: ReadonlySet<string>;
  tempFactionIds: Map<string, string>;
}

export type StrategyApplyResult = { fields: StrategyFields; error: null } | { fields: StrategyFields; error: string };

const RELATION_STATUSES: readonly string[] = ["war", "peace", "alliance"];
const TROOP_TYPES: readonly TroopType[] = ["infantry", "cavalry", "archers_siege"];
const ECONOMY_KEYS: readonly (keyof StrategyRegionEconomy)[] = [
  "population",
  "wealth",
  "manpower",
  "unrest",
  "garrison",
];
const BOOLEAN_RULES: readonly (keyof StrategyRules)[] = [
  "agents_enabled",
  "revolt_talks_enabled",
  "letters_enabled",
  "judgments_enabled",
];
const NUMBER_RULES: readonly (keyof StrategyRules)[] = [
  "bribe_base_price",
  "trade_value_per_turn",
  "trade_income_percent",
  "access_value_per_turn",
  "conditional_trigger_percent",
  "conditional_gate_percent",
  "oath_offer_min_opinion",
  "oath_offer_duration_turns",
  "letter_cooldown_turns",
  "judgment_cooldown_turns",
  "judgment_sentence_turns",
];

const parsePayload = (content: string): Payload | null => {
  try {
    const parsed: unknown = JSON.parse(content);
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Payload) : null;
  } catch {
    return null;
  }
};

const readText = (value: unknown): string | null => (typeof value === "string" ? value : null);

const readNumber = (value: unknown): number | null =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const resolveId = (value: unknown, context: StrategyApplyContext): string | null => {
  const text = readText(value);
  return text === null ? null : (context.tempFactionIds.get(text) ?? text);
};

const findFactionId = (fields: StrategyFields, value: unknown, context: StrategyApplyContext): string | null => {
  const id = resolveId(value, context);
  return id !== null && fields.factions.some((item) => item.id === id) ? id : null;
};

const LEADER_ALIAS_SUFFIX = "_ruler";

const findNewFactionLeaderId = (fields: StrategyFields, id: string, context: StrategyApplyContext): string | null => {
  const tempKey = id.endsWith(LEADER_ALIAS_SUFFIX) ? id.slice(0, -LEADER_ALIAS_SUFFIX.length) : id;
  const factionId = context.tempFactionIds.get(tempKey);
  return fields.factions.find((item) => item.id === factionId)?.leader_id ?? null;
};

const findLeaderId = (fields: StrategyFields, value: unknown, context: StrategyApplyContext): string | null => {
  const id = readText(value);
  if (id === null) return null;
  if (fields.leaders.some((item) => item.id === id)) return id;
  return findNewFactionLeaderId(fields, id, context);
};

const findRegionId = (value: unknown, context: StrategyApplyContext): string | null => {
  const id = readText(value);
  return id !== null && context.knownRegionIds.has(id) ? id : null;
};

const buildFactionPatch = (payload: Payload, capitalId: string | null) => ({
  capital_region_id: capitalId,
  ...(readNumber(payload.treasury) === null ? {} : { treasury: clampWholeNumber(payload.treasury as number) }),
  ...(readNumber(payload.manpower) === null ? {} : { manpower: clampWholeNumber(payload.manpower as number) }),
  ...(readNumber(payload.stability) === null ? {} : { stability: clampWholeNumber(payload.stability as number, 100) }),
  ...(typeof payload.is_playable === "boolean" ? { is_playable: payload.is_playable } : {}),
});

const buildLeaderPatch = (payload: Payload) => ({
  ...(readText(payload.leader_name) ? { name: readText(payload.leader_name) as string } : {}),
  ...(readText(payload.leader_history) === null ? {} : { history: readText(payload.leader_history) as string }),
});

const findFactionByName = (fields: StrategyFields, name: string) =>
  fields.factions.find((item) => item.name.trim().toLowerCase() === name.toLowerCase());

const applyFaction = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const name = readText(payload.name)?.trim();
  if (!name) return "A faction needs a name.";
  const capitalId = payload.capital_region_id == null ? null : findRegionId(payload.capital_region_id, context);
  if (payload.capital_region_id != null && capitalId === null) return "That capital region doesn't exist on the map.";
  const existing = findFactionByName(fields, name);
  const added = existing ? fields : addFaction(fields, name);
  const faction = existing ?? added.factions[added.factions.length - 1];
  const tempId = readText(payload.temp_id);
  if (tempId) context.tempFactionIds.set(tempId, faction.id);
  const updated = updateFaction(added, faction.id, buildFactionPatch(payload, capitalId));
  return updateLeader(updated, faction.leader_id ?? "", buildLeaderPatch(payload));
};

const applyLeaderHistory = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const leaderId = findLeaderId(fields, payload.leader_id, context);
  const history = readText(payload.history);
  if (leaderId === null) return "That ruler doesn't exist.";
  if (history === null) return "The history must be text.";
  return updateLeader(fields, leaderId, { history });
};

const applyRelation = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const factionA = findFactionId(fields, payload.faction_a, context);
  const factionB = findFactionId(fields, payload.faction_b, context);
  const status = readText(payload.status);
  if (factionA === null || factionB === null || factionA === factionB) return "Pick two existing, different factions.";
  if (status === null || !RELATION_STATUSES.includes(status)) return "Status must be war, peace or alliance.";
  return setRelation(fields, factionA, factionB, status as RelationStatus);
};

const applyClaim = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const factionId = findFactionId(fields, payload.faction_id, context);
  const regionId = findRegionId(payload.region_id, context);
  if (factionId === null || regionId === null) return "The claim needs an existing faction and region.";
  return addClaim(fields, factionId, regionId);
};

const applyGrudge = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const holderId = findLeaderId(fields, payload.holder_id, context);
  const targetId = findLeaderId(fields, payload.target_id, context);
  if (holderId === null || targetId === null || holderId === targetId) return "A grudge needs two different existing rulers.";
  const opinion = readNumber(payload.opinion);
  const patch = {
    ...(opinion === null ? {} : { opinion }),
    ...(readText(payload.reason) === null ? {} : { reason: readText(payload.reason) as string }),
  };
  return updateGrudge(addGrudge(fields, holderId, targetId), holderId, targetId, patch);
};

const readEconomyPatch = (payload: Payload): Partial<StrategyRegionEconomy> => {
  const patch: Partial<StrategyRegionEconomy> = {};
  for (const key of ECONOMY_KEYS) {
    const value = readNumber(payload[key]);
    if (value !== null) patch[key] = value;
  }
  return patch;
};

const applyRegionSetup = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const regionId = findRegionId(payload.region_id, context);
  if (regionId === null) return "That region doesn't exist on the map.";
  const hasOwner = "owner_id" in payload;
  const ownerId = payload.owner_id == null ? null : findFactionId(fields, payload.owner_id, context);
  if (hasOwner && payload.owner_id != null && ownerId === null) return "That owner faction doesn't exist.";
  const owned = hasOwner ? setRegionOwner(fields, regionId, ownerId) : fields;
  return updateRegionEconomy(owned, regionId, readEconomyPatch(payload));
};

const readTroops = (value: unknown): Partial<Record<TroopType, number>> => {
  const source = value !== null && typeof value === "object" ? (value as Payload) : {};
  const troops: Partial<Record<TroopType, number>> = {};
  for (const type of TROOP_TYPES) {
    const count = readNumber(source[type]);
    if (count !== null) troops[type] = clampWholeNumber(count);
  }
  return troops;
};

const hasIdenticalArmy = (
  fields: StrategyFields,
  ownerId: string,
  locationId: string,
  troops: Partial<Record<TroopType, number>>,
): boolean =>
  fields.armies.some(
    (army) =>
      army.owner_id === ownerId &&
      army.location_id === locationId &&
      TROOP_TYPES.every((type) => (army.troops[type] ?? 0) === (troops[type] ?? 0)),
  );

const applyArmy = (fields: StrategyFields, payload: Payload, context: StrategyApplyContext): BlockResult => {
  const ownerId = findFactionId(fields, payload.owner_id, context);
  const locationId = findRegionId(payload.location_id, context);
  if (ownerId === null || locationId === null) return "An army needs an existing faction and region.";
  const troops = readTroops(payload.troops);
  if (hasIdenticalArmy(fields, ownerId, locationId, troops)) return fields;
  const added = addArmy(fields, ownerId, locationId);
  const army = added.armies[added.armies.length - 1];
  const withTroops = Object.keys(troops).length > 0 ? updateArmy(added, army.id, { troops }) : added;
  const commanderName = readText(payload.commander_name)?.trim();
  return commanderName ? setArmyCommander(withTroops, army.id, { name: commanderName }) : withTroops;
};

const applyTiming = (fields: StrategyFields, payload: Payload): BlockResult => {
  const patch: Partial<StrategyTiming> = {};
  for (const key of ["start_year", "start_month", "end_year"] as const) {
    const value = readNumber(payload[key]);
    if (value !== null) patch[key] = Math.trunc(value);
  }
  return setTiming(fields, patch);
};

const applyRules = (fields: StrategyFields, payload: Payload): BlockResult => {
  const patch: Partial<StrategyRules> = {};
  for (const key of BOOLEAN_RULES) {
    if (typeof payload[key] === "boolean") (patch[key] as boolean) = payload[key] as boolean;
  }
  for (const key of NUMBER_RULES) {
    const value = readNumber(payload[key]);
    if (value !== null) (patch[key] as number) = value;
  }
  return Object.keys(patch).length > 0 ? setRules(fields, patch) : "That rules suggestion changes nothing.";
};

const applyByTarget = (
  fields: StrategyFields,
  target: string,
  payload: Payload,
  context: StrategyApplyContext,
): BlockResult => {
  if (target === "faction") return applyFaction(fields, payload, context);
  if (target === "leader_history") return applyLeaderHistory(fields, payload, context);
  if (target === "relation") return applyRelation(fields, payload, context);
  if (target === "claim") return applyClaim(fields, payload, context);
  if (target === "grudge") return applyGrudge(fields, payload, context);
  if (target === "region_setup") return applyRegionSetup(fields, payload, context);
  if (target === "army") return applyArmy(fields, payload, context);
  if (target === "timing") return applyTiming(fields, payload);
  if (target === "rules") return applyRules(fields, payload);
  return "This suggestion type can't be applied here.";
};

export const applyStrategyBlock = (
  fields: StrategyFields,
  block: ActionBlock,
  context: StrategyApplyContext,
): StrategyApplyResult => {
  const payload = parsePayload(block.content);
  if (payload === null) return { fields, error: "Couldn't read that suggestion — invalid data." };
  const result = applyByTarget(fields, block.target, payload, context);
  return typeof result === "string" ? { fields, error: result } : { fields: result, error: null };
};
