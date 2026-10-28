import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import type { ScenarioResponse } from "../types/scenario.types";
import { CARD_TEST_SCENARIO_ID, installCardApi, type CardApiState } from "./cardApiMock";
import { EDIT_CONFLICT_CODE, HTTP_STATUS_CONFLICT } from "../constants/editGuard";
import { SCENARIO_TOOLS } from "@/shared/constants/scenario-tools";
import type { ConditionResponse } from "../types/condition.types";
import type { EndConditionResponse } from "../types/end_condition.types";
import type { EntityResponse } from "../types/entity.types";
import type { FactResponse } from "../types/fact.types";
import type { InvariantResponse } from "../types/invariant.types";
import type { MinigameResponse } from "../types/minigame.types";
import type { RuleCheckResponse } from "../types/ruleCheck.types";
import type { SheetRuleResponse } from "../types/sheetRule.types";
import type { ScenarioToolsResponse } from "../types/scenarioTools.types";

export const STUDIO_TEST_SCENARIO_ID = CARD_TEST_SCENARIO_ID;
const FIRST_STAMP = "2026-10-27T10:00:00Z";

export const buildScenarioFixture = (
  overrides: Partial<ScenarioResponse> = {},
): ScenarioResponse =>
  ({
    scenario_id: STUDIO_TEST_SCENARIO_ID,
    creator_id: "user-1",
    creator_display_name: "Creator",
    is_bookmarked: false,
    can_review: false,
    title: "",
    logline: null,
    mode: "newbie",
    status: "draft",
    genre_tags: [],
    complexity_tier: "newbie",
    player_count_support: "solo",
    estimated_playtime: null,
    cover_image_url: null,
    content_tag: null,
    publish_error: null,
    published_at: null,
    play_count: 0,
    rating_avg: "0",
    narrator_persona: null,
    world_data: {},
    setup_schema: [],
    state_schema: {},
    end_conditions: [],
    checkpoints: [],
    rules: {},
    opening_scene: null,
    narration_font: null,
    narrator_voice_name: null,
    action_chips: [],
    setup_archetypes: [],
    current_version: 1,
    created_at: FIRST_STAMP,
    updated_at: FIRST_STAMP,
    visibility: "private",
    mood_tags: [],
    player_mode: "written",
    content_edited_at: FIRST_STAMP,
    ...overrides,
  }) as ScenarioResponse;

export const buildConditionFixture = (
  overrides: Partial<ConditionResponse> & Pick<ConditionResponse, "condition_id">,
): ConditionResponse => ({
  scenario_id: STUDIO_TEST_SCENARIO_ID,
  label: "Rule",
  condition_expression: {},
  condition_version: "1",
  narrator_instruction: "",
  metadata: {},
  state_mutation: null,
  state_mutations: [],
  is_one_shot: false,
  sensory_cue: null,
  cut_ambient: false,
  silence_duration_ms: 0,
  ...overrides,
});

export const buildEndConditionFixture = (
  overrides: Partial<EndConditionResponse> & Pick<EndConditionResponse, "end_condition_id">,
): EndConditionResponse => ({
  scenario_id: STUDIO_TEST_SCENARIO_ID,
  condition_expression: {},
  outcome_tag: "win",
  outcome_title: "Ending",
  outcome_text: "",
  is_secret: false,
  priority: 0,
  metadata: null,
  ...overrides,
});

export const buildInvariantFixture = (
  overrides: Partial<InvariantResponse> & Pick<InvariantResponse, "invariant_id">,
): InvariantResponse => ({
  scenario_id: STUDIO_TEST_SCENARIO_ID,
  label: "Limit",
  invariant_expression: {},
  applies_to: "player",
  narrator_text: "",
  metadata: null,
  ...overrides,
});

export const buildRuleCheckFixture = (
  overrides: Partial<RuleCheckResponse> & Pick<RuleCheckResponse, "check_id">,
): RuleCheckResponse =>
  ({ scenario_id: STUDIO_TEST_SCENARIO_ID, label: "Check", priority: 0, ...overrides }) as RuleCheckResponse;

export const buildSheetRuleFixture = (
  overrides: Partial<SheetRuleResponse> & Pick<SheetRuleResponse, "rule_id">,
): SheetRuleResponse =>
  ({ scenario_id: STUDIO_TEST_SCENARIO_ID, key: "rule", number: 1, text: "Rule", ...overrides }) as SheetRuleResponse;

export const buildMinigameFixture = (
  overrides: Partial<MinigameResponse> & Pick<MinigameResponse, "minigame_id">,
): MinigameResponse =>
  ({
    scenario_id: STUDIO_TEST_SCENARIO_ID,
    label: "Game",
    minigame_type: "dodge",
    priority: 0,
    ...overrides,
  }) as MinigameResponse;

export interface StudioApiState extends CardApiState {
  scenario: ScenarioResponse | null;
  scenarioCreates: Array<Record<string, unknown>>;
  scenarioUpdates: Array<Record<string, unknown>>;
  entityTypeCreates: Array<Record<string, unknown>>;
  conditions: ConditionResponse[];
  endConditions: EndConditionResponse[];
  invariants: InvariantResponse[];
  conditionWrites: Array<Record<string, unknown>>;
  endConditionWrites: Array<Record<string, unknown>>;
  invariantWrites: Array<Record<string, unknown>>;
  endingReorders: string[][];
  ruleChecks: RuleCheckResponse[];
  sheetRules: SheetRuleResponse[];
  minigames: MinigameResponse[];
  toolPuts: string[][];
  contentStampCount: number;
  writeLog: string[];
}

interface StudioApiInit {
  scenario?: ScenarioResponse | null;
  entities?: EntityResponse[];
  facts?: FactResponse[];
  conditions?: ConditionResponse[];
  endConditions?: EndConditionResponse[];
  invariants?: InvariantResponse[];
  ruleChecks?: RuleCheckResponse[];
  sheetRules?: SheetRuleResponse[];
  minigames?: MinigameResponse[];
  enabledTools?: string[];
}

const closeOverToolRequirements = (requested: string[]): ScenarioToolsResponse => {
  const closed = new Set(requested);
  SCENARIO_TOOLS.filter((tool) => requested.includes(tool.key)).forEach((tool) =>
    tool.requires.forEach((required) => closed.add(required)),
  );
  const ordered = SCENARIO_TOOLS.map((tool) => tool.key).filter((key) => closed.has(key));
  return {
    enabled_tools: ordered,
    auto_enabled: ordered.filter((key) => !requested.includes(key)),
    inert_data: {},
  };
};

const bumpContentStamp = (state: StudioApiState): void => {
  if (!state.scenario) return;
  state.contentStampCount += 1;
  state.scenario = {
    ...state.scenario,
    content_edited_at: `child-write-${state.contentStampCount}`,
  };
};

interface CollectionBinding<Row> {
  path: string;
  onWrite: () => void;
  idKey: keyof Row & string;
  read: () => Row[];
  write: (rows: Row[]) => void;
  writes: Array<Record<string, unknown>>;
  build: (body: Record<string, unknown>, index: number) => Row;
}

const installCollectionHandlers = <Row extends object>(
  binding: CollectionBinding<Row>,
): void => {
  const base = `*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}/${binding.path}`;
  const idOf = (row: Row): string => String(row[binding.idKey]);
  server.use(
    http.get(base, () => HttpResponse.json({ items: binding.read() })),
    http.post(base, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      binding.writes.push(body);
      const created = binding.build(body, binding.read().length + 1);
      binding.write([...binding.read(), created]);
      binding.onWrite();
      return HttpResponse.json(created, { status: 201 });
    }),
    http.patch(`${base}/:rowId`, async ({ request, params }) => {
      const body = (await request.json()) as Record<string, unknown>;
      binding.writes.push(body);
      binding.write(
        binding.read().map((row) =>
          idOf(row) === String(params.rowId) ? ({ ...row, ...body } as Row) : row,
        ),
      );
      binding.onWrite();
      return HttpResponse.json(binding.read().find((row) => idOf(row) === String(params.rowId)));
    }),
    http.delete(`${base}/:rowId`, ({ params }) => {
      binding.write(binding.read().filter((row) => idOf(row) !== String(params.rowId)));
      binding.onWrite();
      return new HttpResponse(null, { status: 204 });
    }),
  );
};

const installEndingReorderHandler = (state: StudioApiState): void => {
  server.use(
    http.post(
      `*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}/end_conditions/reorder`,
      async ({ request }) => {
        const body = (await request.json()) as { ordered_end_condition_ids: string[] };
        state.endingReorders.push(body.ordered_end_condition_ids);
        state.endConditions = body.ordered_end_condition_ids.flatMap((id, priority) => {
          const row = state.endConditions.find((item) => item.end_condition_id === id);
          return row ? [{ ...row, priority }] : [];
        });
        bumpContentStamp(state);
        return HttpResponse.json({ items: state.endConditions });
      },
    ),
  );
};

const installRuleHandlers = (state: StudioApiState): void => {
  installEndingReorderHandler(state);
  installCollectionHandlers<ConditionResponse>({
    path: "conditions",
    onWrite: () => bumpContentStamp(state),
    idKey: "condition_id",
    read: () => state.conditions,
    write: (rows) => {
      state.conditions = rows;
    },
    writes: state.conditionWrites,
    build: (body, index) => buildConditionFixture({ condition_id: `condition-${index}`, ...body }),
  });
  installCollectionHandlers<EndConditionResponse>({
    path: "end_conditions",
    onWrite: () => bumpContentStamp(state),
    idKey: "end_condition_id",
    read: () => state.endConditions,
    write: (rows) => {
      state.endConditions = rows;
    },
    writes: state.endConditionWrites,
    build: (body, index) =>
      buildEndConditionFixture({ end_condition_id: `ending-${index}`, priority: index - 1, ...body }),
  });
  installCollectionHandlers<InvariantResponse>({
    path: "invariants",
    onWrite: () => bumpContentStamp(state),
    idKey: "invariant_id",
    read: () => state.invariants,
    write: (rows) => {
      state.invariants = rows;
    },
    writes: state.invariantWrites,
    build: (body, index) => buildInvariantFixture({ invariant_id: `limit-${index}`, ...body }),
  });
};

const installToolRowHandlers = (state: StudioApiState): void => {
  const noWrites: Array<Record<string, unknown>> = [];
  installCollectionHandlers<RuleCheckResponse>({
    path: "rule-checks",
    onWrite: () => bumpContentStamp(state),
    idKey: "check_id",
    read: () => state.ruleChecks,
    write: (rows) => {
      state.ruleChecks = rows;
    },
    writes: noWrites,
    build: (body, index) => buildRuleCheckFixture({ check_id: `check-${index}`, ...body }),
  });
  installCollectionHandlers<SheetRuleResponse>({
    path: "sheet-rules",
    onWrite: () => bumpContentStamp(state),
    idKey: "rule_id",
    read: () => state.sheetRules,
    write: (rows) => {
      state.sheetRules = rows;
    },
    writes: noWrites,
    build: (body, index) => buildSheetRuleFixture({ rule_id: `sheet-${index}`, ...body }),
  });
  installCollectionHandlers<MinigameResponse>({
    path: "minigames",
    onWrite: () => bumpContentStamp(state),
    idKey: "minigame_id",
    read: () => state.minigames,
    write: (rows) => {
      state.minigames = rows;
    },
    writes: noWrites,
    build: (body, index) => buildMinigameFixture({ minigame_id: `game-${index}`, ...body }),
  });
};

const installToolHandlers = (state: StudioApiState): void => {
  const url = `*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}/tools`;
  const readEnabled = (): string[] => state.scenario?.enabled_tools ?? [];
  server.use(
    http.get(url, () =>
      HttpResponse.json({ enabled_tools: readEnabled(), auto_enabled: [], inert_data: {} }),
    ),
    http.put(url, async ({ request }) => {
      const body = (await request.json()) as { enabled_tools: string[] };
      state.toolPuts.push(body.enabled_tools);
      state.writeLog.push("tools");
      if (state.scenario?.mode !== "master" && body.enabled_tools.length > 0) {
        return HttpResponse.json({ detail: "Tools require Advanced mode." }, { status: 409 });
      }
      const enabledNow = state.scenario?.enabled_tools ?? [];
      const hasRequiredToolRemoved = enabledNow.some(
        (key) =>
          !body.enabled_tools.includes(key) &&
          SCENARIO_TOOLS.some((tool) => body.enabled_tools.includes(tool.key) && tool.requires.includes(key as never)),
      );
      if (hasRequiredToolRemoved) {
        return HttpResponse.json({ detail: "A tool still needs this one." }, { status: 409 });
      }
      const result = closeOverToolRequirements(body.enabled_tools);
      state.scenario = { ...state.scenario, enabled_tools: result.enabled_tools } as ScenarioResponse;
      bumpContentStamp(state);
      return HttpResponse.json(result);
    }),
  );
};

export const installStudioApi = (init: StudioApiInit = {}): StudioApiState => {
  const cardApi = installCardApi({ entities: init.entities ?? [], facts: init.facts ?? [] });
  const state = cardApi as StudioApiState;
  state.scenario = init.scenario ?? null;
  state.scenarioCreates = [];
  state.scenarioUpdates = [];
  state.entityTypeCreates = [];
  state.conditions = init.conditions ?? [];
  state.endConditions = init.endConditions ?? [];
  state.invariants = init.invariants ?? [];
  state.conditionWrites = [];
  state.endConditionWrites = [];
  state.invariantWrites = [];
  state.endingReorders = [];
  state.ruleChecks = init.ruleChecks ?? [];
  state.sheetRules = init.sheetRules ?? [];
  state.minigames = init.minigames ?? [];
  state.toolPuts = [];
  state.contentStampCount = 0;
  state.writeLog = [];
  if (state.scenario && init.enabledTools) {
    state.scenario = { ...state.scenario, enabled_tools: init.enabledTools };
  }
  installRuleHandlers(state);
  installToolRowHandlers(state);
  installToolHandlers(state);
  server.use(
    http.get("*/v1/scenarios/:scenarioId", () =>
      state.scenario
        ? HttpResponse.json(state.scenario)
        : HttpResponse.json({ detail: "missing" }, { status: 404 }),
    ),
    http.post("*/v1/scenarios", async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      state.scenarioCreates.push(body);
      state.scenario = buildScenarioFixture(body as Partial<ScenarioResponse>);
      return HttpResponse.json(state.scenario, { status: 201 });
    }),
    http.patch("*/v1/scenarios/:scenarioId", async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      state.scenarioUpdates.push(body);
      state.writeLog.push(`scenario:${Object.keys(body).filter((key) => key !== "expected_content_edited_at").join(",")}`);
      const { expected_content_edited_at: stamp, ...fields } = body;
      if (stamp && stamp !== state.scenario?.content_edited_at) {
        return HttpResponse.json({ code: EDIT_CONFLICT_CODE }, { status: HTTP_STATUS_CONFLICT });
      }
      state.scenario = { ...state.scenario, ...fields } as ScenarioResponse;
      return HttpResponse.json(state.scenario);
    }),
    http.get(`*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}/entity-types`, () =>
      HttpResponse.json({ items: [] }),
    ),
    http.post(`*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}/entity-types`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      state.entityTypeCreates.push(body);
      bumpContentStamp(state);
      return HttpResponse.json(
        { scenario_entity_type_id: "type-1", scenario_id: STUDIO_TEST_SCENARIO_ID, attributes_schema: {}, ...body },
        { status: 201 },
      );
    }),
  );
  return state;
};
