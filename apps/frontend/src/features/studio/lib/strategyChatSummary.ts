import type { ActionBlock, AssistantStrategyContextPayload } from "../types/assistant.types";

type Payload = Record<string, unknown>;

interface NameBook {
  factions: Map<string, string>;
  leaders: Map<string, string>;
  regions: Map<string, string>;
}

const LEADER_ALIAS_SUFFIX = "_ruler";

const parsePayload = (content: string): Payload | null => {
  try {
    const parsed: unknown = JSON.parse(content);
    return parsed !== null && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Payload) : null;
  } catch {
    return null;
  }
};

const text = (value: unknown): string | null => (typeof value === "string" && value.trim() ? value.trim() : null);

const registerEarlierFaction = (book: NameBook, payload: Payload): void => {
  const tempId = text(payload.temp_id);
  const name = text(payload.name);
  if (!tempId || !name) return;
  book.factions.set(tempId, name);
  book.leaders.set(`${tempId}${LEADER_ALIAS_SUFFIX}`, text(payload.leader_name) ?? `${name}'s ruler`);
};

const buildNameBook = (context: AssistantStrategyContextPayload, earlier: readonly ActionBlock[]): NameBook => {
  const book: NameBook = {
    factions: new Map(context.factions.map((faction) => [faction.faction_id, faction.name])),
    leaders: new Map(
      context.factions.flatMap((faction) => (faction.leader_id ? [[faction.leader_id, faction.leader_name] as const] : [])),
    ),
    regions: new Map(context.regions.map((region) => [region.region_id, region.name || region.region_id])),
  };
  for (const block of earlier) {
    const payload = block.target === "faction" ? parsePayload(block.content) : null;
    if (payload) registerEarlierFaction(book, payload);
  }
  return book;
};

const nameOf = (names: Map<string, string>, value: unknown): string => {
  const id = text(value);
  return id === null ? "unknown" : (names.get(id) ?? id);
};

const describeFaction = (payload: Payload, book: NameBook): string => {
  const ruler = text(payload.leader_name);
  const capital = payload.capital_region_id == null ? null : nameOf(book.regions, payload.capital_region_id);
  const parts = [`Found ${text(payload.name) ?? "a faction"}`];
  if (ruler) parts.push(`ruled by ${ruler}`);
  if (capital) parts.push(`capital ${capital}`);
  return parts.join(", ");
};

const describeTroops = (value: unknown): string => {
  const troops = value !== null && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const parts = Object.entries(troops).filter(([, count]) => typeof count === "number" && count > 0);
  return parts.length ? parts.map(([type, count]) => `${count} ${type.replace("_", "/")}`).join(", ") : "no troops";
};

const describeRegionSetup = (payload: Payload, book: NameBook): string => {
  const changes = ["population", "wealth", "manpower", "unrest", "garrison"].filter((key) => key in payload);
  const owner = "owner_id" in payload ? `owner ${payload.owner_id == null ? "none" : nameOf(book.factions, payload.owner_id)}` : null;
  const detail = [owner, changes.length ? `sets ${changes.join(", ")}` : null].filter(Boolean).join("; ");
  return `${nameOf(book.regions, payload.region_id)}: ${detail || "no changes"}`;
};

const describeRules = (payload: Payload): string => `Rules: ${Object.keys(payload).join(", ") || "no changes"}`;

const describeTiming = (payload: Payload): string => {
  const start = payload.start_year === undefined ? null : `from year ${payload.start_year}`;
  const end = payload.end_year === undefined ? null : `to year ${payload.end_year}`;
  return `Timeline ${[start, end].filter(Boolean).join(" ") || "unchanged"}`;
};

const describePayload = (target: string, payload: Payload, book: NameBook): string | null => {
  if (target === "faction") return describeFaction(payload, book);
  if (target === "leader_history") return `Backstory for ${nameOf(book.leaders, payload.leader_id)}`;
  if (target === "relation") {
    return `${nameOf(book.factions, payload.faction_a)} and ${nameOf(book.factions, payload.faction_b)}: ${text(payload.status) ?? "unknown"}`;
  }
  if (target === "claim") return `${nameOf(book.factions, payload.faction_id)} claims ${nameOf(book.regions, payload.region_id)}`;
  if (target === "grudge") {
    return `${nameOf(book.leaders, payload.holder_id)} resents ${nameOf(book.leaders, payload.target_id)} (opinion ${payload.opinion ?? "unchanged"})`;
  }
  if (target === "region_setup") return describeRegionSetup(payload, book);
  if (target === "army") {
    return `${nameOf(book.factions, payload.owner_id)} army at ${nameOf(book.regions, payload.location_id)}: ${describeTroops(payload.troops)}`;
  }
  if (target === "timing") return describeTiming(payload);
  if (target === "rules") return describeRules(payload);
  return null;
};

export const describeStrategyBlock = (
  block: ActionBlock,
  context: AssistantStrategyContextPayload,
  earlier: readonly ActionBlock[],
): string | null => {
  if (block.target === "title") return `Rename the scenario to "${block.content.trim()}"`;
  const payload = parsePayload(block.content);
  if (payload === null) return null;
  return describePayload(block.target, payload, buildNameBook(context, earlier));
};
