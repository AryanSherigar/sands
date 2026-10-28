import {
  PlaythroughResponse,
  ParticipantSummary,
} from "@/shared/api/playthroughs.api";
import { TurnLogListResponse } from "../api/turns.api";
import {
  CharacterSetupField,
  EntityAttributeSchemaField,
  EntityType,
  MasterEntity,
  Objective,
  PlayerStat,
  PlaythroughData,
  StoryCard,
  TurnLogItem,
} from "../types/play.types";
import { ScenarioMood } from "@/shared/types/audio.types";
import { buildChapterDeltaFromToolCalls } from "../utils/chapterDelta";
import { readDisplayHints } from "@/shared/lib/hud/readDisplayHints";
import { MinigameEventPayload } from "@/shared/types/minigame.types";
import {
  PendingCheckState,
  RuleCheckEventPayload,
  isRuleCheckPayload,
} from "@/shared/types/check.types";

const DEFAULT_OPENING_PREMISE = "Your chronicle begins...";

// NOTE: legacy newbie scenarios store these keys in Scenario.world_data; new
// stories write documents that the backend renders into the same keys.
interface NewbieWorldData {
  worldLore?: string;
  openingPrompt?: string;
  singleLorePrompt?: string;
  initial_mood?: string;
  facts?: { id: number; text: string }[];
  storyCards?: { id: string; type: string; name: string; content: string }[];
}

interface SetupSchemaField {
  key: string;
  label: string;
}

interface MasterEntitySnapshot {
  entity_id: string;
  entity_type: EntityType;
  canonical_name: string;
  aliases: string[];
  description: string | null;
  attributes_schema: Record<string, EntityAttributeSchemaField>;
  obtainable: boolean | null;
}

interface MasterFactSnapshot {
  fact_id: string;
  text: string;
}

interface EndConditionSnapshot {
  outcome_tag: "win" | "lose";
  outcome_title: string;
  outcome_text: string;
  is_secret: boolean;
}

interface StateSchemaFieldSnapshot {
  type: string;
  label?: string;
  fields?: Record<string, StateSchemaFieldSnapshot>;
}

interface CommonPlaythroughFields {
  playthrough_id: string;
  scenario_id: string;
  scenario_title: string;
  mode: "newbie" | "master" | "strategy";
  initial_mood?: ScenarioMood;
  music_tracks?: Partial<Record<ScenarioMood, string | null>>;
  tier_tracks?: Record<string, string>;
  narration_font?: string | null;
  action_chips: string[];
  duties: string[];
  enabled_tools: string[];
  creator_name: string;
  character_name: string;
  custom_fields: CharacterSetupField[];
  is_spectator: boolean;
  participant_id: string | null;
  can_act: boolean;
  next_actor_label: string | null;
  ended_outcome_tag: "win" | "lose" | null;
  ended_outcome_title: string | null;
  ended_outcome_text: string | null;
}

/** Solo playthroughs always allow acting. Multiplayer cycles by turn_order_position. */
function computeCanAct(
  participants: ParticipantSummary[],
  myParticipantId: string,
  turnCount: number,
): boolean {
  if (participants.length <= 1) return true;
  const ordered = [...participants].sort(
    (a, b) => a.turn_order_position - b.turn_order_position,
  );
  const expected = ordered[turnCount % ordered.length];
  return expected?.participant_id === myParticipantId;
}

/** Display label for the bottom bar's "Waiting for X..." state. */
function computeNextActorLabel(
  participants: ParticipantSummary[],
  turnCount: number,
): string | null {
  if (participants.length <= 1) return null;
  const ordered = [...participants].sort(
    (a, b) => a.turn_order_position - b.turn_order_position,
  );
  const next = ordered[turnCount % ordered.length];
  return next ? `Player ${next.turn_order_position}` : null;
}

/** Maps submitted setup values to their creator-authored labels from setup_schema. */
function buildCustomFields(
  setupMap: Record<string, unknown>,
  setupSchema: SetupSchemaField[],
): CharacterSetupField[] {
  const labelByKey = new Map(
    setupSchema.map((field) => [field.key, field.label]),
  );
  return Object.entries(setupMap)
    .filter(([key]) => key !== "character_name")
    .map(([key, value]) => ({
      key,
      label: labelByKey.get(key) ?? key,
      value: Array.isArray(value) ? value.join(", ") : String(value ?? ""),
    }));
}

function titleCaseKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function readEnabledTools(snapshot: Record<string, unknown> | undefined): string[] {
  const pinned = snapshot?.enabled_tools;
  if (!Array.isArray(pinned)) return [];
  return pinned.filter((tool): tool is string => typeof tool === "string");
}

const MAX_DUTIES = 4;

function readDuties(snapshot: Record<string, unknown> | undefined): string[] {
  const worldData = snapshot?.world_data;
  if (typeof worldData !== "object" || worldData === null) return [];
  const duties = (worldData as { duties?: unknown }).duties;
  if (!Array.isArray(duties)) return [];
  return duties
    .filter((duty): duty is string => typeof duty === "string")
    .slice(0, MAX_DUTIES);
}

function buildCommonFields(
  serverPlaythrough: PlaythroughResponse,
  isSpectatorMode: boolean,
  mode: "newbie" | "master" | "strategy",
  initialMood: ScenarioMood | undefined,
  setupMap: Record<string, unknown>,
  setupSchema: SetupSchemaField[],
): CommonPlaythroughFields {
  const canAct = computeCanAct(
    serverPlaythrough.participants,
    serverPlaythrough.participant_id,
    serverPlaythrough.turn_count,
  );
  const nextActorLabel = computeNextActorLabel(
    serverPlaythrough.participants,
    serverPlaythrough.turn_count,
  );
  const narrationFont =
    (serverPlaythrough.scenario_snapshot?.narration_font as string | null) ??
    null;
  const musicTracks = serverPlaythrough.scenario_snapshot?.music_tracks as
    Partial<Record<ScenarioMood, string | null>> | undefined;
  const tierTracks = serverPlaythrough.scenario_snapshot?.tier_tracks as
    Record<string, string> | undefined;
  const actionChips =
    (serverPlaythrough.scenario_snapshot?.action_chips as
      string[] | undefined) ?? [];
  return {
    playthrough_id: serverPlaythrough.playthrough_id,
    scenario_id: serverPlaythrough.scenario_id,
    scenario_title: serverPlaythrough.scenario_title,
    mode,
    initial_mood: initialMood,
    music_tracks: musicTracks,
    tier_tracks: tierTracks,
    narration_font: narrationFont,
    action_chips: actionChips,
    duties: readDuties(serverPlaythrough.scenario_snapshot),
    enabled_tools: readEnabledTools(serverPlaythrough.scenario_snapshot),
    creator_name: "Scenario Creator",
    character_name: (setupMap.character_name as string) || "Adventurer",
    custom_fields: buildCustomFields(setupMap, setupSchema),
    is_spectator: isSpectatorMode,
    participant_id: isSpectatorMode ? null : serverPlaythrough.participant_id,
    can_act: canAct,
    next_actor_label: nextActorLabel,
    ended_outcome_tag: serverPlaythrough.ended_outcome_tag,
    ended_outcome_title: serverPlaythrough.ended_outcome_title,
    ended_outcome_text: serverPlaythrough.ended_outcome_text,
  };
}

export function buildNewbiePlaythroughData(
  serverPlaythrough: PlaythroughResponse,
  turnsData: TurnLogListResponse | undefined,
  isSpectatorMode: boolean,
): PlaythroughData {
  const setupMap = (serverPlaythrough.state?.setup || {}) as Record<
    string,
    unknown
  >;
  const snapshot = serverPlaythrough.scenario_snapshot || {};
  const worldData = (snapshot.world_data ?? {}) as NewbieWorldData;
  const setupSchema = (snapshot.setup_schema ?? []) as SetupSchemaField[];

  const turns: TurnLogItem[] = (turnsData?.items ?? []).map((turn) => ({
    id: turn.turn_id,
    turn_number: turn.turn_number,
    action_mode: turn.action_mode,
    action_text: turn.action_text,
    narration_text: turn.narration_text ?? "",
    created_at: turn.created_at,
    image_url: turn.image_url ?? undefined,
    audio_url: turn.audio_url ?? undefined,
  }));

  return {
    ...buildCommonFields(
      serverPlaythrough,
      isSpectatorMode,
      "newbie",
      (worldData.initial_mood as ScenarioMood) || undefined,
      setupMap,
      setupSchema,
    ),
    opening_premise:
      readRenderedOpeningScene(serverPlaythrough.state ?? {}) ||
      worldData.openingPrompt ||
      worldData.singleLorePrompt ||
      DEFAULT_OPENING_PREMISE,
    world_lore:
      worldData.worldLore ||
      worldData.singleLorePrompt ||
      "No world lore recorded.",
    key_facts: (worldData.facts ?? []).map((fact) => fact.text),
    story_cards: (worldData.storyCards ?? []).map((card): StoryCard => ({
      id: card.id,
      title: card.name,
      category: card.type,
      content: card.content,
    })),
    turns,
    entities: [],
    active_conditions: [],
    objectives: [],
    player_stats: [],
    player_inventory: [],
    pending_minigame: null,
    pending_check: null,
    pending_rule_check: null,
    server_time_ms: serverPlaythrough.server_time_ms ?? null,
    state: serverPlaythrough.state ?? {},
    hud_hints: { meters: [] },
    rule_sheet: serverPlaythrough.rule_sheet ?? [],
  };
}

export function buildStrategyPlaythroughData(
  serverPlaythrough: PlaythroughResponse,
  turnsData: TurnLogListResponse | undefined,
  isSpectatorMode: boolean,
): PlaythroughData {
  return {
    ...buildNewbiePlaythroughData(
      serverPlaythrough,
      turnsData,
      isSpectatorMode,
    ),
    mode: "strategy",
  };
}

function buildMasterEntities(
  snapshot: Record<string, unknown>,
  state: Record<string, unknown>,
): MasterEntity[] {
  const entitiesSnapshot = (snapshot.entities ?? []) as MasterEntitySnapshot[];
  const liveStates = (state.entities ?? {}) as Record<
    string,
    Record<string, unknown>
  >;
  return entitiesSnapshot.map((entity) => ({
    ...entity,
    attributes: liveStates[entity.entity_id] ?? {},
  }));
}

function buildPlayerStats(
  playerFields: Record<string, StateSchemaFieldSnapshot>,
  playerState: Record<string, unknown>,
): PlayerStat[] {
  return Object.entries(playerFields)
    .filter(([, field]) => field.type !== "entity_ref" && field.type !== "list")
    .map(([key, field]) => ({
      key,
      label: field.label ?? titleCaseKey(key),
      value: playerState[key],
    }));
}

function buildPlayerInventory(
  playerFields: Record<string, StateSchemaFieldSnapshot>,
  playerState: Record<string, unknown>,
  entities: MasterEntity[],
): MasterEntity[] {
  const entityById = new Map(entities.map((e) => [e.entity_id, e]));
  const inventoryIds = Object.entries(playerFields)
    .filter(([, field]) => field.type === "list")
    .flatMap(([key]) => (playerState[key] as string[] | undefined) ?? []);
  return inventoryIds
    .map((id) => entityById.get(id))
    .filter((e): e is MasterEntity => e !== undefined);
}

// The pending-minigame marker is TRS-infrastructure-only, stamped into
// working_state["_pending_minigame"] by minigame_trigger_evaluator and
// cleared by minigame_result_resolver — never authored/edited by a creator,
// so it's read straight off the raw state blob rather than a snapshot field.
function buildPendingMinigame(
  state: Record<string, unknown>,
): MinigameEventPayload | null {
  const raw = state._pending_minigame;
  if (!raw || typeof raw !== "object") return null;
  return raw as MinigameEventPayload;
}

// Same TRS-infrastructure-only pattern as buildPendingMinigame above —
// stamped by pipeline.py's _stamp_pending_check, cleared by
// check_result_resolver.py once resolved.
function buildPendingCheck(
  state: Record<string, unknown>,
): PendingCheckState | null {
  const raw = state._pending_check;
  if (!raw || typeof raw !== "object" || isRuleCheckPayload(raw)) return null;
  return raw as PendingCheckState;
}

// A rule check shares the `_pending_check` marker with the dice check; it is
// told apart by its `kind`, which a dice check never carries.
function buildPendingRuleCheck(
  state: Record<string, unknown>,
): RuleCheckEventPayload | null {
  const raw = state._pending_check;
  return isRuleCheckPayload(raw) ? raw : null;
}

function readRenderedOpeningScene(state: Record<string, unknown>): string {
  const narrative = state.narrative as { opening_prompt?: unknown } | undefined;
  const renderedScene = narrative?.opening_prompt;
  return typeof renderedScene === "string" && renderedScene.trim()
    ? renderedScene
    : "";
}

function buildMasterOpeningPremise(state: Record<string, unknown>): string {
  return readRenderedOpeningScene(state) || DEFAULT_OPENING_PREMISE;
}

function buildMasterKeyFacts(snapshot: Record<string, unknown>): string[] {
  const facts = (snapshot.facts ?? []) as MasterFactSnapshot[];
  return facts.map((fact) => fact.text);
}

function buildObjectives(snapshot: Record<string, unknown>): Objective[] {
  const endConditions = (snapshot.end_conditions ??
    []) as EndConditionSnapshot[];
  return endConditions
    .filter((ec) => !ec.is_secret)
    .map((ec) => ({
      outcome_title: ec.outcome_title,
      outcome_tag: ec.outcome_tag,
      outcome_text: ec.outcome_text,
    }));
}

export function buildMasterPlaythroughData(
  serverPlaythrough: PlaythroughResponse,
  turnsData: TurnLogListResponse | undefined,
  isSpectatorMode: boolean,
): PlaythroughData {
  const setupMap = (serverPlaythrough.state?.setup || {}) as Record<
    string,
    unknown
  >;
  const snapshot = serverPlaythrough.scenario_snapshot || {};
  const setupSchema = (snapshot.setup_schema ?? []) as SetupSchemaField[];
  const state = serverPlaythrough.state || {};

  const entities = buildMasterEntities(snapshot, state);
  const stateSchema = (snapshot.state_schema ?? {}) as Record<
    string,
    StateSchemaFieldSnapshot
  >;
  const playerFields = stateSchema.player?.fields ?? {};
  const playerState = (state.player ?? {}) as Record<string, unknown>;

  const turns: TurnLogItem[] = (turnsData?.items ?? []).map((turn) => ({
    id: turn.turn_id,
    turn_number: turn.turn_number,
    action_mode: turn.action_mode,
    action_text: turn.action_text,
    narration_text: turn.narration_text ?? "",
    created_at: turn.created_at,
    chapter_delta: buildChapterDeltaFromToolCalls(turn.tool_calls, entities),
    image_url: turn.image_url ?? undefined,
    audio_url: turn.audio_url ?? undefined,
  }));

  return {
    ...buildCommonFields(
      serverPlaythrough,
      isSpectatorMode,
      "master",
      undefined,
      setupMap,
      setupSchema,
    ),
    opening_premise: buildMasterOpeningPremise(state),
    world_lore: "",
    key_facts: buildMasterKeyFacts(snapshot),
    story_cards: [],
    turns,
    entities,
    active_conditions: serverPlaythrough.active_conditions ?? [],
    objectives: buildObjectives(snapshot),
    player_stats: buildPlayerStats(playerFields, playerState),
    player_inventory: buildPlayerInventory(playerFields, playerState, entities),
    pending_minigame: buildPendingMinigame(state),
    pending_check: buildPendingCheck(state),
    pending_rule_check: buildPendingRuleCheck(state),
    server_time_ms: serverPlaythrough.server_time_ms ?? null,
    state,
    hud_hints: readDisplayHints(stateSchema),
    rule_sheet: serverPlaythrough.rule_sheet ?? [],
  };
}
