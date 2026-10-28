import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { usePlaytestStore } from "../../stores/playtest.store";
import { useToastStore } from "@/shared/stores/toast.store";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildConditionFixture,
  buildEndConditionFixture,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";
import { buildEntityFixture } from "../../test/cardApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const SCENARIO_BASE = `*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}`;
const WAIT = { timeout: 4000 };
const ENDINGS_STEP = 7;
const RULES_STEP = 9;
const STATE_SCHEMA = {
  lantern_oil: { type: "number" as const, label: "Lantern oil", min: 0, max: 10, initial: 10, description: "Light left" },
  has_escaped: { type: "boolean" as const, label: "Has escaped", initial: false, description: "Got out" },
  sanity: { type: "number" as const, label: "Sanity", min: 0, max: 10, initial: 10, hidden: true, description: "Calm" },
};
const READY = {
  mode: "master" as const,
  title: "The Door Below",
  logline: "A door in the sea.",
  opening_scene: "The tide is out, {player_name}.",
  state_schema: STATE_SCHEMA,
};

interface Calls {
  starts: Array<Record<string, unknown>>;
}

const sseBody = (events: Array<[string, string]>): ReadableStream<Uint8Array> => {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      events.forEach(([name, data]) =>
        controller.enqueue(encoder.encode(`event: ${name}\ndata: ${data}\n\n`)),
      );
      controller.close();
    },
  });
};

const installPlaytestApi = (
  options: { startResponse?: () => Response; turnEvents?: Array<[string, string]> } = {},
) => {
  const calls: Calls = { starts: [] };
  const turnEvents = options.turnEvents ?? [
    ["state_update", JSON.stringify({ state: { lantern_oil: 1, has_escaped: true } })],
    ["narration", "The door opens."],
    ["done", "{}"],
  ];
  server.use(
    http.post(`${SCENARIO_BASE}/playtest`, async ({ request }) => {
      calls.starts.push((await request.json()) as Record<string, unknown>);
      if (options.startResponse) return options.startResponse();
      return HttpResponse.json({
        playthrough_id: `pt-${calls.starts.length}`,
        participant_id: "part-1",
        scenario_snapshot: {},
        state: { lantern_oil: 2, has_escaped: false, narrative: { opening_prompt: "The tide is out." } },
      });
    }),
    http.post("*/v1/turn", () => new HttpResponse(sseBody(turnEvents), { headers: { "Content-Type": "text/event-stream" } })),
    http.get("*/v1/playthroughs/:id", () =>
      HttpResponse.json({ state: { lantern_oil: 1, has_escaped: true }, playthrough_id: "pt-1" }),
    ),
  );
  return calls;
};

const openStudio = async (step: number, init: Parameters<typeof installStudioApi>[0] = {}) => {
  const api = installStudioApi({
    scenario: buildScenarioFixture(READY),
    endConditions: [
      buildEndConditionFixture({
        end_condition_id: "e1",
        outcome_title: "Lights out",
        condition_expression: { field: "lantern_oil", op: "<=", value: 2 },
      }),
    ],
    ...init,
  });
  renderStudio({ path: EDIT_PATH });
  await screen.findByRole("tab", { name: "Guide" });
  await waitFor(() => expect(useStudioTabsStore.getState().isResumePending).toBe(false), WAIT);
  act(() => useStudioTabsStore.getState().setGuideStep(step));
  return api;
};

const clickTestEnding = async (): Promise<void> => {
  const user = userEvent.setup();
  const card = await screen.findByRole("article", { name: "Ending 1" }, WAIT);
  await user.click(within(card).getByRole("button", { name: "Ending 1 options" }));
  await user.click(screen.getByRole("menuitem", { name: "Test this ending" }));
};

describe("Test this ending", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    usePlaytestStore.getState().endSession();
    usePlaytestStore.getState().clearPendingTest();
  });

  it("opens the Playtest tab split to the right and starts it with the preset values", async () => {
    const calls = installPlaytestApi();
    await openStudio(ENDINGS_STEP);
    await clickTestEnding();

    await waitFor(() => expect(calls.starts).toHaveLength(1), WAIT);
    expect(calls.starts[0]).toMatchObject({ state_overrides: { lantern_oil: 2 } });
    expect(useStudioTabsStore.getState().splitTabId).toBe("playtest");
  });

  it("lists every tracked value, hidden ones without a number, and follows the state update", async () => {
    installPlaytestApi();
    await openStudio(ENDINGS_STEP);
    await clickTestEnding();

    const readout = await screen.findByRole("region", { name: "Tracked values" }, WAIT);
    expect(readout).toHaveTextContent("Lantern oil: 2");
    expect(readout).toHaveTextContent("Has escaped: no");
    expect(readout).toHaveTextContent("Sanity: hidden from players");

    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("What do you do?", undefined, WAIT), "I wait");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await waitFor(() => expect(readout).toHaveTextContent("Lantern oil: 1"), WAIT);
    expect(readout).toHaveTextContent("Has escaped: yes");
  });

  it("restarts as a plain playtest afterwards", async () => {
    const calls = installPlaytestApi();
    await openStudio(ENDINGS_STEP);
    await clickTestEnding();
    await screen.findByRole("region", { name: "Tracked values" }, WAIT);

    await userEvent.setup().click(screen.getByRole("button", { name: "Restart with my changes" }));

    await waitFor(() => expect(calls.starts).toHaveLength(2), WAIT);
    expect(calls.starts[1]).not.toHaveProperty("state_overrides");
  });

  it("shows the server's message plainly when the preset is rejected", async () => {
    installPlaytestApi({
      startResponse: () => HttpResponse.json({ detail: "Lantern oil must be between 0 and 10." }, { status: 422 }),
    });
    await openStudio(ENDINGS_STEP);
    await clickTestEnding();

    expect(await screen.findByRole("alert", undefined, WAIT)).toHaveTextContent("Lantern oil must be between 0 and 10.");
  });

  it("tells the creator to write the opening first when the story has none", async () => {
    useToastStore.setState({ queue: [] });
    const calls = installPlaytestApi();
    await openStudio(ENDINGS_STEP, { scenario: buildScenarioFixture({ ...READY, opening_scene: null }) });
    await clickTestEnding();

    await waitFor(
      () =>
        expect(useToastStore.getState().queue.map((item) => item.message)).toContain(
          "Write your opening first. The playtest starts from it.",
        ),
      WAIT,
    );
    expect(calls.starts).toHaveLength(0);
  });

  it("saves an ending edit that is still waiting before it starts the test", async () => {
    let titleAtStart = "";
    const api = await openStudio(ENDINGS_STEP);
    installPlaytestApi({
      startResponse: () => {
        titleAtStart = api.endConditions[0].outcome_title;
        return HttpResponse.json({
          playthrough_id: "pt-1",
          participant_id: "part-1",
          scenario_snapshot: {},
          state: { lantern_oil: 2 },
        });
      },
    });
    const user = userEvent.setup();
    const card = await screen.findByRole("article", { name: "Ending 1" }, WAIT);
    await user.type(within(card).getByLabelText("Title"), "!");
    await user.click(within(card).getByRole("button", { name: "Ending 1 options" }));
    await user.click(screen.getByRole("menuitem", { name: "Test this ending" }));

    await waitFor(() => expect(titleAtStart).not.toBe(""), WAIT);
    expect(titleAtStart).toBe("Lights out!");
  });

  it("saves a rule edit that is still waiting before it starts the test", async () => {
    let instructionAtStart: string | null = null;
    const api = await openStudio(RULES_STEP, {
      endConditions: [],
      conditions: [
        buildConditionFixture({
          condition_id: "c1",
          label: "When Has escaped becomes yes",
          narrator_instruction: "x",
          condition_expression: { field: "has_escaped", op: "==", value: true },
        }),
      ],
    });
    installPlaytestApi({
      startResponse: () => {
        instructionAtStart = api.conditions[0].narrator_instruction;
        return HttpResponse.json({
          playthrough_id: "pt-1",
          participant_id: "part-1",
          scenario_snapshot: {},
          state: { has_escaped: true },
        });
      },
    });
    const user = userEvent.setup();
    const card = await screen.findByRole("article", { name: /Rule 1/ }, WAIT);
    await user.type(within(card).getByLabelText("Tell the narrator"), "y");
    await user.click(within(card).getByRole("button", { name: /options/ }));
    await user.click(screen.getByRole("menuitem", { name: "Test this rule" }));

    await waitFor(() => expect(instructionAtStart).not.toBeNull(), WAIT);
    expect(instructionAtStart).toBe("xy");
  });

  it("starts the rule test from the rule's When sentence", async () => {
    const calls = installPlaytestApi();
    await openStudio(RULES_STEP, {
      endConditions: [],
      conditions: [
        buildConditionFixture({
          condition_id: "c1",
          label: "When Has escaped becomes yes",
          condition_expression: { field: "has_escaped", op: "==", value: true },
        }),
      ],
    });
    const user = userEvent.setup();
    const card = await screen.findByRole("article", { name: /Rule 1/ }, WAIT);
    await user.click(within(card).getByRole("button", { name: /options/ }));
    await user.click(screen.getByRole("menuitem", { name: "Test this rule" }));

    await waitFor(() => expect(calls.starts).toHaveLength(1), WAIT);
    expect(calls.starts[0]).toMatchObject({ state_overrides: { has_escaped: true } });
  });

  it("explains that card values cannot be preset", async () => {
    const calls = installPlaytestApi();
    await openStudio(ENDINGS_STEP, {
      entities: [
        buildEntityFixture({
          entity_id: "mara",
          canonical_name: "Mara",
          attributes_schema: { trust: { type: "number", label: "Trust", min: 0, max: 10, initial: 5 } },
        }),
      ],
      endConditions: [
        buildEndConditionFixture({
          end_condition_id: "e1",
          outcome_title: "She leaves",
          condition_expression: { field: "mara.trust", op: "<=", value: 0 },
        }),
      ],
    });
    await clickTestEnding();

    await waitFor(() => expect(calls.starts).toHaveLength(1), WAIT);
    expect(calls.starts[0]).not.toHaveProperty("state_overrides");
    expect(await screen.findByText(/Card values can't be preset in a test yet/)).toBeInTheDocument();
  });
});
