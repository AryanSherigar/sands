import type { BattleSummary, CampaignWorldView } from "../types/simulation.types";

const REQUIRED_ARRAY_FIELDS = ["regions", "armies", "rivals", "queued_orders"] as const;
const REQUIRED_OBJECT_FIELDS = ["clock", "my_faction", "ruler"] as const;
const REQUIRED_NUMBER_FIELDS = ["turn", "world_version", "orders_remaining"] as const;

const OPTIONAL_ARRAY_FIELDS = [
  "battles",
  "pending_demands",
  "pending_calls",
  "alliances",
  "vassalages",
  "coalitions",
  "truces",
  "own_hostages",
  "own_prisoners",
  "open_mediations",
  "subsidies",
] as const;

const INVALID_WORLD_MESSAGE = "The simulation returned an unreadable world";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function findMissingField(payload: Record<string, unknown>): string | null {
  const missingArray = REQUIRED_ARRAY_FIELDS.find((field) => !Array.isArray(payload[field]));
  if (missingArray) return missingArray;
  const missingObject = REQUIRED_OBJECT_FIELDS.find((field) => !isRecord(payload[field]));
  if (missingObject) return missingObject;
  return REQUIRED_NUMBER_FIELDS.find((field) => typeof payload[field] !== "number") ?? null;
}

function normalizeOptionalArrays(world: Record<string, unknown>): Record<string, unknown> {
  const normalized: Record<string, unknown> = { ...world };
  for (const field of OPTIONAL_ARRAY_FIELDS) {
    if (!Array.isArray(normalized[field])) {
      normalized[field] = [];
    }
  }
  return normalized;
}

const BATTLE_STATUSES: BattleSummary["status"][] = ["awaiting_commands", "awaiting_next_turn", "resolved"];

function toBattleStatus(value: unknown): BattleSummary["status"] {
  return BATTLE_STATUSES.find((status) => status === value) ?? "awaiting_commands";
}

function toBattleView(pending: Record<string, unknown>): BattleSummary | null {
  if (typeof pending.id !== "string" || typeof pending.region_id !== "string") return null;
  return {
    id: pending.id,
    region_id: pending.region_id,
    status: toBattleStatus(pending.status),
    outcome: typeof pending.outcome === "string" ? pending.outcome : null,
    exchanges_used: typeof pending.exchanges_used === "number" ? pending.exchanges_used : 0,
    total_exchanges: typeof pending.total_exchanges === "number" ? pending.total_exchanges : 0,
    is_big: pending.is_big === true,
    control_mode: pending.control_mode as BattleSummary["control_mode"],
    current_turn: typeof pending.current_turn === "number" ? pending.current_turn : undefined,
  };
}

// NOTE: after a reload /world carries in-flight battles only as `pending_battles`;
// mutation responses carry `battles`, so fall back to the pending list when it is empty.
function deriveBattles(world: Record<string, unknown>): Record<string, unknown> {
  const pending = world.pending_battles;
  const hasBattles = Array.isArray(world.battles) && world.battles.length > 0;
  if (hasBattles || !Array.isArray(pending)) return world;
  const derived = pending.filter(isRecord).map(toBattleView).filter((view) => view !== null);
  return { ...world, battles: derived };
}

export function parseCampaignWorld(payload: unknown): CampaignWorldView {
  if (!isRecord(payload)) throw new Error(INVALID_WORLD_MESSAGE);
  const missingField = findMissingField(payload);
  if (missingField) throw new Error(`${INVALID_WORLD_MESSAGE}: missing ${missingField}`);
  return normalizeOptionalArrays(deriveBattles(payload)) as unknown as CampaignWorldView;
}
