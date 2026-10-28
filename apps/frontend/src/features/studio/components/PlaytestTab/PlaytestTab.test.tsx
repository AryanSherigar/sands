import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { NAME_SETUP_FIELD } from "../../constants/guideChips";
import { server } from "@/test/msw/server";
import { usePlaytestStore } from "../../stores/playtest.store";
import { useStudioStore } from "../../stores/studio.store";
import { useStudioTabsStore } from "../../stores/studioTabs.store";
import { renderStudio } from "../../test/renderStudio";
import {
  STUDIO_TEST_SCENARIO_ID,
  buildScenarioFixture,
  installStudioApi,
} from "../../test/studioApiMock";

const EDIT_PATH = `/studio/${STUDIO_TEST_SCENARIO_ID}/edit`;
const SCENARIO_BASE = `*/v1/scenarios/${STUDIO_TEST_SCENARIO_ID}`;
const WAIT = { timeout: 4000 };
const READY = {
  title: "The Door Below",
  logline: "A door in the sea.",
  opening_scene: "The tide is out, {player_name}.",
  setup_schema: [NAME_SETUP_FIELD],
};

interface PlaytestCalls {
  starts: Array<{ setup_values: Record<string, unknown> }>;
  turns: Array<Record<string, unknown>>;
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

const installPlaytestApi = (turnEvents: Array<[string, string]> = [["narration", "The door opens."], ["done", "{}"]]) => {
  const calls: PlaytestCalls = { starts: [], turns: [] };
  server.use(
    http.post(`${SCENARIO_BASE}/playtest`, async ({ request }) => {
      calls.starts.push((await request.json()) as PlaytestCalls["starts"][number]);
      return HttpResponse.json({
        playthrough_id: `pt-${calls.starts.length}`,
        participant_id: "part-1",
        scenario_snapshot: {},
        state: { narrative: { opening_prompt: "The tide is out, Tester." } },
      });
    }),
    http.post("*/v1/turn", async ({ request }) => {
      calls.turns.push((await request.json()) as Record<string, unknown>);
      return new HttpResponse(sseBody(turnEvents), {
        headers: { "Content-Type": "text/event-stream" },
      });
    }),
  );
  return calls;
};

const openStudio = async (init: Parameters<typeof installStudioApi>[0] = {}) => {
  const api = installStudioApi({ scenario: buildScenarioFixture(READY), ...init });
  const view = renderStudio({ path: EDIT_PATH });
  await screen.findByRole("tab", { name: "Guide" });
  return { api, ...view };
};

const openPlaytest = async (): Promise<void> => {
  await userEvent.setup().click(screen.getByRole("button", { name: "Playtest" }));
};

describe("Playtest tab", () => {
  beforeEach(() => {
    localStorage.clear();
    useStudioTabsStore.getState().resetTabs();
    useStudioStore.getState().setHasEditConflict(false);
    usePlaytestStore.getState().endSession();
  });

  it("opens split to the right from the top bar and starts a private playtest", async () => {
    const calls = installPlaytestApi();
    await openStudio();
    await openPlaytest();

    const split = await screen.findByRole("region", { name: "Split tab" });
    expect(useStudioTabsStore.getState().splitTabId).toBe("playtest");
    expect(within(split).getByText("Playtest — not visible to players.")).toBeInTheDocument();
    expect(await within(split).findByText("The tide is out, Tester.", undefined, WAIT)).toBeInTheDocument();
    expect(calls.starts).toEqual([{ setup_values: { character_name: "Tester" } }]);
  });

  it("focuses the tab instead of starting a second playtest when it is already open", async () => {
    const calls = installPlaytestApi();
    await openStudio();
    await openPlaytest();
    await screen.findByText("The tide is out, Tester.", undefined, WAIT);
    await openPlaytest();

    expect(calls.starts).toHaveLength(1);
    expect(useStudioTabsStore.getState().openTabIds.filter((id) => id === "playtest")).toHaveLength(1);
  });

  it("asks for an opening first and starts nothing without one", async () => {
    const calls = installPlaytestApi();
    await openStudio({ scenario: buildScenarioFixture({ ...READY, opening_scene: null }) });
    await openPlaytest();

    expect(await screen.findByText("Write your opening first. The playtest starts from it.")).toBeInTheDocument();
    expect(calls.starts).toHaveLength(0);
    await userEvent.setup().click(screen.getByRole("button", { name: "Go to Opening" }));
    expect(await screen.findByRole("heading", { name: "Where does the story begin?" })).toBeInTheDocument();
  });

  it("streams the narrator's reply to what the creator does", async () => {
    const calls = installPlaytestApi();
    await openStudio();
    await openPlaytest();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("What do you do?", undefined, WAIT), "I push the door");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("The door opens.", undefined, WAIT)).toBeInTheDocument();
    expect(screen.getByText("I push the door")).toBeInTheDocument();
    expect(calls.turns[0]).toMatchObject({
      playthrough_id: "pt-1",
      participant_id: "part-1",
      action_text: "I push the door",
      action_kind: "narrative",
    });
  });

  it("says plainly when the narrator fails and lets the creator try again", async () => {
    installPlaytestApi([["degraded", "The narrator is resting."]]);
    await openStudio();
    await openPlaytest();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("What do you do?", undefined, WAIT), "Look");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("alert", undefined, WAIT)).toHaveTextContent("The narrator is resting.");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("restarts with the current draft as a new playtest and clears the transcript", async () => {
    const calls = installPlaytestApi();
    await openStudio();
    await openPlaytest();
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("What do you do?", undefined, WAIT), "I push the door");
    await user.click(screen.getByRole("button", { name: "Send" }));
    await screen.findByText("The door opens.", undefined, WAIT);

    await user.click(screen.getByRole("button", { name: "Restart with my changes" }));

    await waitFor(() => expect(calls.starts).toHaveLength(2), WAIT);
    await waitFor(() => expect(screen.queryByText("The door opens.")).toBeNull(), WAIT);
    expect(usePlaytestStore.getState().playthroughId).toBe("pt-2");
  });

  it("flags edits made during a playtest and lets the creator keep playing", async () => {
    installPlaytestApi();
    const { api } = await openStudio();
    server.use(
      http.patch(SCENARIO_BASE, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        api.scenario = { ...api.scenario!, ...body, content_edited_at: "2026-10-27T11:00:00Z" } as typeof api.scenario;
        return HttpResponse.json(api.scenario);
      }),
    );
    await openPlaytest();
    await screen.findByText("The tide is out, Tester.", undefined, WAIT);
    expect(screen.queryByText("You've changed the story since this playtest began.")).toBeNull();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Story name"), "!");
    expect(await screen.findByText("You've changed the story since this playtest began.", undefined, WAIT)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Keep playing" }));
    expect(screen.queryByText("You've changed the story since this playtest began.")).toBeNull();
  });

  it("ends the playtest and closes the tab", async () => {
    installPlaytestApi();
    await openStudio();
    await openPlaytest();
    await screen.findByText("The tide is out, Tester.", undefined, WAIT);
    await userEvent.setup().click(screen.getByRole("button", { name: "End playtest" }));

    expect(useStudioTabsStore.getState().openTabIds).not.toContain("playtest");
    expect(usePlaytestStore.getState().playthroughId).toBeNull();
    expect(screen.queryByText("Playtest — not visible to players.")).toBeNull();
  });

  it("asks for the other setup choices before starting and sends them", async () => {
    const calls = installPlaytestApi();
    await openStudio({
      scenario: buildScenarioFixture({
        ...READY,
        setup_schema: [
          NAME_SETUP_FIELD,
          {
            id: "d",
            key: "difficulty",
            label: "Difficulty",
            type: "single_select",
            required: true,
            options: [
              { id: "g", label: "Gentle", value: "gentle" },
              { id: "n", label: "Normal", value: "normal" },
            ],
            defaultValue: "normal",
          },
        ],
      }),
    });
    await openPlaytest();
    const user = userEvent.setup();
    expect(calls.starts).toHaveLength(0);
    await user.selectOptions(await screen.findByLabelText("Difficulty"), "gentle");
    await user.click(screen.getByRole("button", { name: "Start playtest" }));

    await waitFor(
      () => expect(calls.starts).toEqual([{ setup_values: { character_name: "Tester", difficulty: "gentle" } }]),
      WAIT,
    );
  });

  it("shows a plain message with Try again when the playtest cannot start", async () => {
    let shouldFail = true;
    const calls = installPlaytestApi();
    server.use(
      http.post(`${SCENARIO_BASE}/playtest`, () => {
        if (shouldFail) return HttpResponse.json({ detail: "Playtest quota reached." }, { status: 429 });
        return HttpResponse.json({
          playthrough_id: "pt-ok",
          participant_id: "part-1",
          scenario_snapshot: {},
          state: { narrative: { opening_prompt: "Back again." } },
        });
      }),
    );
    await openStudio();
    await openPlaytest();

    expect(await screen.findByRole("alert", undefined, WAIT)).toHaveTextContent("Couldn't start the playtest.");
    shouldFail = false;
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Back again.", undefined, WAIT)).toBeInTheDocument();
    expect(calls.starts).toHaveLength(0);
  });
});
