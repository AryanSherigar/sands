import type { StateFieldDefinition } from "../types/scenario.types";
export interface CombatActorDraft {
    max_health: string;
    health: string;
    attack: string;
    armor: string;
    speed: string;
    accuracy: string;
    luck: string;
}
export interface CombatDraft {
    title: string;
    trigger: string;
    player: CombatActorDraft;
    opponent: CombatActorDraft;
    recoveryHealth: string;
    recoveryLocationId: string;
    playerAttackTag: string;
    opponentRequiredTag: string;
    outcomeKind: "recover" | "end";
    endingId: string;
}
export const EMPTY_ACTOR: CombatActorDraft = { max_health: "", health: "", attack: "", armor: "", speed: "", accuracy: "", luck: "" };
export function readCombatDraft(value: unknown): CombatDraft | null {
    if (!value || typeof value !== "object" || Array.isArray(value))
        return null;
    const record = value as Record<string, unknown>;
    if (typeof record.encounter_id !== "string" || Object.keys(record).some((key) => !["encounter_id", "title", "start_condition", "player", "opponent", "outcomes", "fallback_outcome_id"].includes(key)))
        return null;
    const start = record.start_condition as Record<string, unknown> | undefined;
    const outcomes = record.outcomes;
    if (typeof record.title !== "string" || !start || typeof start.field !== "string" || start.op !== "==" || start.value !== true ||
        Object.keys(start).some((key) => !["field", "op", "value"].includes(key)) ||
        !Array.isArray(outcomes) || outcomes.length < 1 || outcomes.length > 2)
        return null;
    const items = outcomes as Record<string, unknown>[];
    const recovery = items.find((item) => item?.id === "recovery" && item.kind === "recover" && typeof item.health === "number" && (item.location_id === undefined || typeof item.location_id === "string") && Object.keys(item).every((key) => ["id", "kind", "health", "location_id"].includes(key)));
    const ending = items.find((item) => item?.id === "defeat" && item.kind === "end" && typeof item.ending_id === "string" && Object.keys(item).every((key) => ["id", "kind", "ending_id"].includes(key)));
    if (items.length !== Number(Boolean(recovery)) + Number(Boolean(ending)))
        return null;
    if ((record.fallback_outcome_id === "recovery" && !recovery) || (record.fallback_outcome_id === "defeat" && !ending) || !["recovery", "defeat"].includes(String(record.fallback_outcome_id)))
        return null;
    const readActor = (raw: unknown): CombatActorDraft | null => {
        if (!raw || typeof raw !== "object" || Array.isArray(raw))
            return null;
        const actor = raw as Record<string, unknown>;
        if (Object.keys(actor).some((key) => !["actor_id", "side", "attack_tags", "required_attack_tag", ...Object.keys(EMPTY_ACTOR)].includes(key)))
            return null;
        const draft = { ...EMPTY_ACTOR };
        for (const key of Object.keys(draft) as (keyof CombatActorDraft)[]) {
            if (typeof actor[key] !== "number")
                return null;
            draft[key] = String(actor[key]);
        }
        return draft;
    };
    const player = readActor(record.player);
    const opponent = readActor(record.opponent);
    if (!player || !opponent)
        return null;
    const playerRecord = record.player as Record<string, unknown>;
    const opponentRecord = record.opponent as Record<string, unknown>;
    if (playerRecord.actor_id !== "player" || playerRecord.side !== "player" || opponentRecord.actor_id !== `opponent-${record.encounter_id}` || opponentRecord.side !== "opponent")
        return null;
    const tags = playerRecord.attack_tags;
    if ((tags !== undefined && (!Array.isArray(tags) || tags.length > 1 || (tags.length === 1 && typeof tags[0] !== "string"))) || playerRecord.required_attack_tag || opponentRecord.attack_tags)
        return null;
    if (opponentRecord.required_attack_tag !== undefined && typeof opponentRecord.required_attack_tag !== "string")
        return null;
    return { title: record.title, trigger: start.field, player, opponent,
        recoveryHealth: recovery ? String(recovery.health) : "", recoveryLocationId: recovery?.location_id ? String(recovery.location_id) : "", playerAttackTag: Array.isArray(tags) ? tags[0] ?? "" : "",
        opponentRequiredTag: typeof opponentRecord.required_attack_tag === "string" ? opponentRecord.required_attack_tag : "",
        outcomeKind: record.fallback_outcome_id === "recovery" ? "recover" : "end", endingId: ending ? String(ending.ending_id) : "" };
}
function numbers(actor: CombatActorDraft): Record<keyof CombatActorDraft, number> {
    const result = {} as Record<keyof CombatActorDraft, number>;
    for (const key of Object.keys(actor) as (keyof CombatActorDraft)[]) {
        const value = Number(actor[key]);
        const limit = key === "accuracy" || key === "luck" ? 100 : 10000;
        if (actor[key].trim() === "" || !Number.isInteger(value) || value < 0 || value > limit)
            throw new Error(`Enter a valid ${key.replace("_", " ")}.`);
        result[key] = value;
    }
    if (result.max_health < 1 || result.health < 1 || result.health > result.max_health)
        throw new Error("Starting health must be between 1 and maximum health.");
    return result;
}
export function buildCombatTemplate(draft: CombatDraft, schema: Record<string, StateFieldDefinition>, id: string) {
    if (!draft.title.trim() || !draft.trigger)
        throw new Error("Enter a title and choose an encounter trigger.");
    const player = numbers(draft.player);
    const opponent = numbers(draft.opponent);
    const recovery = Number(draft.recoveryHealth);
    if ((draft.outcomeKind === "recover" || draft.recoveryHealth.trim()) && (!Number.isInteger(recovery) || recovery < 1 || recovery > player.max_health))
        throw new Error("Recovery health must be between 1 and the player's maximum health.");
    if (draft.outcomeKind === "end" && !draft.endingId)
        throw new Error("Choose a defeat ending.");
    const attackTag = draft.playerAttackTag.trim();
    const requiredTag = draft.opponentRequiredTag.trim();
    if (attackTag.length > 128 || requiredTag.length > 128)
        throw new Error("Attack tags must be 128 characters or fewer.");
    if (requiredTag && requiredTag !== attackTag)
        throw new Error("The player's attack must carry the opponent's required tag.");
    const currentPlayer = schema.player;
    if (currentPlayer && currentPlayer.type !== "object")
        throw new Error("The player value must be an object to track health.");
    const existingHealth = currentPlayer?.fields?.health;
    if (existingHealth && (existingHealth.type !== "number" || typeof existingHealth.initial !== "number" || existingHealth.initial !== player.health || (typeof existingHealth.min === "number" && existingHealth.min > 0) || (typeof existingHealth.max === "number" && existingHealth.max < player.max_health)))
        throw new Error("Player health must match the existing starting value, allow zero, and support the maximum health.");
    const health = existingHealth ?? { type: "number" as const, label: "Health", initial: player.health, min: 0, max: player.max_health };
    const nextSchema: Record<string, StateFieldDefinition> = { ...schema, player: { ...currentPlayer, type: "object" as const, fields: { ...currentPlayer?.fields, health } } };
    const outcomes = [
        ...(draft.recoveryHealth.trim() ? [{ id: "recovery", kind: "recover", health: recovery, ...(draft.recoveryLocationId ? { location_id: draft.recoveryLocationId } : {}) }] : []),
        ...(draft.endingId ? [{ id: "defeat", kind: "end", ending_id: draft.endingId }] : []),
    ];
    const encounter = { encounter_id: id, title: draft.title.trim(), start_condition: { field: draft.trigger, op: "==", value: true },
        player: { actor_id: "player", side: "player", ...player, ...(attackTag ? { attack_tags: [attackTag] } : {}) },
        opponent: { actor_id: `opponent-${id}`, side: "opponent", ...opponent, ...(requiredTag ? { required_attack_tag: requiredTag } : {}) },
        outcomes, fallback_outcome_id: draft.outcomeKind === "recover" ? "recovery" : "defeat" };
    return { encounter, stateSchema: nextSchema };
}
