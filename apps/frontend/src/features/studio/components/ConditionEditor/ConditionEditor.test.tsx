import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { ScenarioResponse } from "../../types/scenario.types";
import { ConditionEditor } from "./ConditionEditor";

const API_URL = "http://localhost:8000";
const SCENARIO_ID = "scenario-1";

const buildScenario = (
  overrides: Partial<ScenarioResponse> = {},
): ScenarioResponse => ({
  scenario_id: SCENARIO_ID,
  creator_id: "creator-1",
  creator_display_name: null,
  is_bookmarked: false,
  can_review: false,
  title: "The Hollow Cairn",
  logline: null,
  mode: "master",
  status: "draft",
  genre_tags: [],
  complexity_tier: "master",
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
  state_schema: {
    player: {
      type: "object",
      fields: {
        sanity: { type: "number", label: "Sanity" },
      },
    },
    flags: {
      type: "object",
      fields: {
        entered_cairn: { type: "boolean", label: "Entered the Cairn" },
      },
    },
  },
  end_conditions: [],
  checkpoints: [],
  rules: {},
  opening_scene: null,
  narration_font: null,
  narrator_voice_name: null,
  action_chips: [],
  setup_archetypes: [],
  current_version: 1,
  created_at: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  ...overrides,
});

const renderConditionEditor = (): void => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ConditionEditor scenarioId={SCENARIO_ID} />
    </QueryClientProvider>,
  );
};

const mockBaseHandlers = (): void => {
  server.use(
    http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
      HttpResponse.json(buildScenario()),
    ),
    http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/entities`, () =>
      HttpResponse.json({ items: [] }),
    ),
    http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/conditions`, () =>
      HttpResponse.json({ items: [] }),
    ),
  );
};

describe("ConditionEditor", () => {
  it("builds a ConditionCreate payload with a state_mutation (Effect C)", async () => {
    mockBaseHandlers();
    let capturedPayload: Record<string, unknown> | null = null;
    server.use(
      http.post(
        `${API_URL}/v1/scenarios/${SCENARIO_ID}/conditions`,
        async ({ request }) => {
          capturedPayload = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({
            condition_id: "condition-1",
            scenario_id: SCENARIO_ID,
            ...capturedPayload,
            condition_version: "1",
            metadata: {},
          });
        },
      ),
    );

    const user = userEvent.setup();
    renderConditionEditor();

    await user.click(
      await screen.findByRole("button", { name: /new condition/i }),
    );

    await user.type(
      screen.getByPlaceholderText(/^label$/i),
      "Entered the cairn",
    );
    await user.type(
      screen.getByPlaceholderText(/narrator instruction/i),
      "Sanity drops as the cairn closes in.",
    );

    const fieldInput = screen.getByPlaceholderText("player.health");
    await user.type(fieldInput, "flags.entered_cairn");

    const valueSelect = screen.getAllByRole("combobox")[2];
    await user.selectOptions(valueSelect, "true");

    await user.click(screen.getByRole("button", { name: /add mutation/i }));
    await user.type(screen.getByLabelText(/mutation 1 path/i), "player.sanity");
    await user.selectOptions(
      screen.getByLabelText(/mutation 1 operation/i),
      "decrement",
    );
    await user.type(screen.getByLabelText(/mutation 1 value/i), "2");

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(capturedPayload).toMatchObject({
      label: "Entered the cairn",
      narrator_instruction: "Sanity drops as the cairn closes in.",
      condition_expression: {
        field: "flags.entered_cairn",
        op: "==",
        value: true,
      },
      state_mutations: [
        { path: "player.sanity", op: "decrement", value: "2" },
      ],
      is_one_shot: false,
    });
  });

  it("edits several mutations: add, reorder, remove, and fire once", async () => {
    mockBaseHandlers();
    let capturedPayload: Record<string, unknown> | null = null;
    server.use(
      http.post(
        `${API_URL}/v1/scenarios/${SCENARIO_ID}/conditions`,
        async ({ request }) => {
          capturedPayload = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ condition_id: "c-1", ...capturedPayload });
        },
      ),
    );
    const user = userEvent.setup();
    renderConditionEditor();
    await user.click(
      await screen.findByRole("button", { name: /new condition/i }),
    );
    await user.type(screen.getByPlaceholderText(/^label$/i), "Drain");
    await user.type(screen.getByPlaceholderText(/narrator instruction/i), "x");

    const addButton = screen.getByRole("button", { name: /add mutation/i });
    await user.click(addButton);
    await user.click(addButton);
    await user.click(addButton);
    await user.type(screen.getByLabelText(/mutation 1 path/i), "a.one");
    await user.type(screen.getByLabelText(/mutation 2 path/i), "a.two");
    await user.type(screen.getByLabelText(/mutation 3 path/i), "a.three");

    await user.click(screen.getByRole("button", { name: /move mutation 1 down/i }));
    await user.click(screen.getByRole("button", { name: /remove mutation 3/i }));
    await user.click(screen.getByLabelText(/fire only once/i));
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    const paths = (
      capturedPayload as unknown as { state_mutations: { path: string }[] }
    ).state_mutations.map((mutation) => mutation.path);
    expect(paths).toEqual(["a.two", "a.one"]);
    expect(capturedPayload).toMatchObject({ is_one_shot: true });
  });

  it("caps the list at sixteen mutations", async () => {
    mockBaseHandlers();
    const user = userEvent.setup();
    renderConditionEditor();
    await user.click(
      await screen.findByRole("button", { name: /new condition/i }),
    );
    const addButton = screen.getByRole("button", { name: /add mutation/i });
    for (let i = 0; i < 16; i += 1) await user.click(addButton);
    expect(addButton).toBeDisabled();
    expect(screen.getByText(/up to 16 mutations/i)).toBeInTheDocument();
  });

  it("loads a legacy single state_mutation as a one-item list", async () => {
    mockBaseHandlers();
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/conditions`, () =>
        HttpResponse.json({
          items: [
            {
              condition_id: "legacy-1",
              scenario_id: SCENARIO_ID,
              label: "Legacy",
              condition_expression: {},
              condition_version: "1",
              narrator_instruction: "Old style",
              metadata: {},
              state_mutation: { path: "player.sanity", op: "decrement", value: 1 },
              state_mutations: [],
              is_one_shot: false,
              sensory_cue: null,
              cut_ambient: true,
              silence_duration_ms: 800,
            },
          ],
        }),
      ),
    );
    const user = userEvent.setup();
    renderConditionEditor();
    await user.click(await screen.findByRole("button", { name: /legacy/i }));
    expect(screen.getByLabelText(/mutation 1 path/i)).toHaveValue("player.sanity");
    expect(screen.queryByLabelText(/mutation 2 path/i)).not.toBeInTheDocument();
  });

  it("enforces at most one connective per clause level", async () => {
    mockBaseHandlers();
    const user = userEvent.setup();
    renderConditionEditor();

    await user.click(
      await screen.findByRole("button", { name: /new condition/i }),
    );

    expect(screen.getAllByRole("button", { name: /\+ and/i })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /\+ or/i })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /\+ not/i })).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: /\+ and/i }));
    // Active connective block appears with Remove button
    expect(screen.getByText("AND")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /^remove$/i }),
    ).toBeInTheDocument();
    // Parent no longer renders + OR, only the nested child has + OR (total still 1, not 2)
    expect(screen.getAllByRole("button", { name: /\+ or/i })).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: /^remove$/i }));
    expect(screen.queryByText("AND")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /^remove$/i }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /\+ and/i })).toHaveLength(1);
  });

  it("shows the sound cue section only when atmosphere is on, and sends its fields", async () => {
    server.use(
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}`, () =>
        HttpResponse.json(buildScenario({ enabled_tools: ["status_hud", "atmosphere"] })),
      ),
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/entities`, () =>
        HttpResponse.json({ items: [] }),
      ),
      http.get(`${API_URL}/v1/scenarios/${SCENARIO_ID}/conditions`, () =>
        HttpResponse.json({ items: [] }),
      ),
    );
    let capturedPayload: Record<string, unknown> | null = null;
    server.use(
      http.post(
        `${API_URL}/v1/scenarios/${SCENARIO_ID}/conditions`,
        async ({ request }) => {
          capturedPayload = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ condition_id: "c", ...capturedPayload });
        },
      ),
    );
    const user = userEvent.setup();
    renderConditionEditor();
    await user.click(await screen.findByRole("button", { name: /new condition/i }));
    await user.type(screen.getByPlaceholderText(/^label$/i), "Phone");
    await user.type(screen.getByPlaceholderText(/narrator instruction/i), "It rings.");

    await user.selectOptions(await screen.findByLabelText("Sound cue"), "phone_ring");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(capturedPayload).toMatchObject({
      sensory_cue: "phone_ring",
      cut_ambient: true,
      silence_duration_ms: 800,
    });
  });

  it("hides the sound cue section when atmosphere is off", async () => {
    mockBaseHandlers();
    const user = userEvent.setup();
    renderConditionEditor();
    await user.click(await screen.findByRole("button", { name: /new condition/i }));

    expect(screen.queryByLabelText("Sound cue")).not.toBeInTheDocument();
  });
});
