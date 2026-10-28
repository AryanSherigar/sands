import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { server } from "@/test/msw/server";
import { StrategySceneDialog } from "../StrategySceneDialog";
import type { SceneMessageCallbacks } from "../../../../lib/scene-stream";
import type { SceneViewResponse, TermsCard } from "../../../../types/scene.types";

const streamMock = vi.hoisted(() => ({
  callbacks: null as SceneMessageCallbacks | null,
  start: vi.fn(),
}));

vi.mock("../../../../lib/scene-stream", () => ({
  startSceneMessage: (sceneId: string, text: string, callbacks: SceneMessageCallbacks) => {
    streamMock.callbacks = callbacks;
    streamMock.start(sceneId, text);
    return vi.fn();
  },
}));

const PLAYTHROUGH_ID = "p1";
const SCENE_ID = "s1";
const SCENE_URL = `*/simulation/v1/playthroughs/${PLAYTHROUGH_ID}/scenes/${SCENE_ID}`;
const WORLD = { world_version: 7, turn: 4, wave: 0, status: "awaiting_scene" };

const CARD: TermsCard = {
  proposer_id: "house_carrow",
  counterpart_id: "house_ashford",
  terms: [
    { kind: "non_aggression", faction_a: "house_carrow", faction_b: "house_ashford", duration_turns: 8 },
  ],
  is_confirmed_by_player: false,
  is_confirmed_by_counterpart: true,
};

function buildScene(overrides: Partial<SceneViewResponse> = {}): SceneViewResponse {
  return {
    scene_id: SCENE_ID,
    scene_type: "negotiation",
    status: "opened",
    turn: 4,
    situation: { summary: "Valdren seeks a pact with Mira.", facts: [] },
    participants: [{ participant_id: "mira", kind: "leader", name: "Mira of Ashford", trait_ids: [] }],
    transcript: [{ sequence: 1, player_text: "Peace?", leader_text: "Perhaps." }],
    exchanges_remaining: 5,
    pending_proposal: null,
    outcome: null,
    ...overrides,
  };
}

function renderDialog(onClose = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  client.setQueryData(["simulation-world", PLAYTHROUGH_ID], WORLD);
  render(
    <QueryClientProvider client={client}>
      <StrategySceneDialog playthroughId={PLAYTHROUGH_ID} sceneId={SCENE_ID} onClose={onClose} />
    </QueryClientProvider>,
  );
  return { onClose };
}

function serveScene(scene: SceneViewResponse) {
  server.use(http.get(SCENE_URL, () => HttpResponse.json(scene)));
}

describe("StrategySceneDialog", () => {
  beforeEach(() => {
    streamMock.callbacks = null;
    streamMock.start.mockClear();
  });

  it("reopens an open scene with its transcript and exchanges left", async () => {
    serveScene(buildScene());
    renderDialog();
    expect(await screen.findByText("Peace?")).toBeInTheDocument();
    expect(screen.getByText("Perhaps.")).toBeInTheDocument();
    expect(screen.getByText("Valdren seeks a pact with Mira.")).toBeInTheDocument();
    expect(screen.getByText("5 exchanges left")).toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("streams the reply, then shows the recorded exchange from the server", async () => {
    let reads = 0;
    server.use(
      http.get(SCENE_URL, () => {
        reads += 1;
        const transcript =
          reads === 1
            ? []
            : [{ sequence: 1, player_text: "Ten turns?", leader_text: "Eight, no fewer." }];
        return HttpResponse.json(buildScene({ transcript, exchanges_remaining: 6 - reads + 1 }));
      }),
    );
    renderDialog();
    const box = await screen.findByLabelText("Your words");
    fireEvent.change(box, { target: { value: "Ten turns?" } });
    fireEvent.click(screen.getByRole("button", { name: "Speak" }));
    expect(streamMock.start).toHaveBeenCalledWith(SCENE_ID, "Ten turns?");
    expect(await screen.findByText("Ten turns?")).toBeInTheDocument();
    act(() => streamMock.callbacks?.onNarration("Eight, "));
    act(() => streamMock.callbacks?.onNarration("no fewer."));
    expect(screen.getByText("Eight, no fewer.")).toBeInTheDocument();
    await act(async () => streamMock.callbacks?.onDone());
    await waitFor(() => expect(reads).toBeGreaterThan(1));
    expect(await screen.findByText("Eight, no fewer.")).toBeInTheDocument();
  });

  it("shows a stream failure and keeps the box usable", async () => {
    serveScene(buildScene());
    renderDialog();
    const box = await screen.findByLabelText("Your words");
    fireEvent.change(box, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Speak" }));
    act(() => streamMock.callbacks?.onFailure("The scene could not continue."));
    expect(await screen.findByRole("alert")).toHaveTextContent("The scene could not continue.");
    expect(screen.getByLabelText("Your words")).toBeEnabled();
  });

  it("shows the outcome when repeated failures ended the scene by default", async () => {
    let reads = 0;
    server.use(
      http.get(SCENE_URL, () => {
        reads += 1;
        return HttpResponse.json(
          reads === 1
            ? buildScene()
            : buildScene({
                status: "defaulted",
                outcome: { kind: "terms_card", result: "refused" },
              }),
        );
      }),
    );
    renderDialog();
    const box = await screen.findByLabelText("Your words");
    fireEvent.change(box, { target: { value: "Hello" } });
    fireEvent.click(screen.getByRole("button", { name: "Speak" }));
    act(() => streamMock.callbacks?.onFailure("The scene could not continue and has ended."));
    expect(await screen.findByRole("status")).toHaveTextContent("The pact was refused.");
  });

  it("confirms the pending terms with the operation guard and the card's sequence", async () => {
    serveScene(buildScene({ pending_proposal: CARD, pending_proposal_sequence: 3 }));
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post(`${SCENE_URL}/decision`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ status: "planning" });
      }),
    );
    renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: "Sign the pact" }));
    await waitFor(() => expect(body).not.toBeNull());
    expect(body).toMatchObject({
      is_confirmed: true,
      proposal_sequence: 3,
      expected_world_version: 7,
      expected_turn: 4,
      expected_wave: 0,
    });
    expect(typeof (body as unknown as { operation_id: string }).operation_id).toBe("string");
  });

  it("leaves the table as a declined decision", async () => {
    serveScene(buildScene());
    let body: Record<string, unknown> | null = null;
    server.use(
      http.post(`${SCENE_URL}/decision`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ status: "planning" });
      }),
    );
    renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: "Leave the table" }));
    await waitFor(() => expect(body).toMatchObject({ is_confirmed: false }));
  });

  it("labels an offer from a rival and lets the player decline it", async () => {
    serveScene(buildScene({ initiator: "ai", is_declinable: true }));
    renderDialog();
    expect(await screen.findByText("Incoming offer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Leave the table" })).toBeInTheDocument();
  });

  it("offers no way out of a forced scene", async () => {
    serveScene(buildScene({ initiator: "ai", is_declinable: false, pending_proposal: CARD }));
    renderDialog();
    expect(await screen.findByRole("button", { name: "Sign the pact" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Decline" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Leave the table" })).not.toBeInTheDocument();
  });

  it("explains that the terms changed when the card was replaced", async () => {
    serveScene(buildScene({ pending_proposal: CARD, pending_proposal_sequence: 1 }));
    server.use(
      http.post(`${SCENE_URL}/decision`, () =>
        HttpResponse.json({ detail: "the terms changed", code: "terms_changed" }, { status: 409 }),
      ),
    );
    const { onClose } = renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: "Sign the pact" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The terms changed while you were reading.",
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  it("reports a rejected decision without closing", async () => {
    serveScene(buildScene({ pending_proposal: CARD }));
    server.use(
      http.post(`${SCENE_URL}/decision`, () =>
        HttpResponse.json({ detail: "scene already resolved", code: "invalid_lifecycle" }, { status: 409 }),
      ),
    );
    const { onClose } = renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: "Sign the pact" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("scene already resolved");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("shows the outcome of a finished scene and closes on request", async () => {
    serveScene(
      buildScene({
        status: "resolved",
        outcome: { kind: "terms_card", result: "agreed", terms_card: CARD },
      }),
    );
    const { onClose } = renderDialog();
    expect(await screen.findByRole("status")).toHaveTextContent("The pact is sealed.");
    expect(screen.queryByLabelText("Your words")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Close" })[0]);
    expect(onClose).toHaveBeenCalled();
  });

  it("renders nothing for a scene that is not a negotiation", async () => {
    serveScene(buildScene({ scene_type: "event" }));
    renderDialog();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByText("Valdren seeks a pact with Mira.")).not.toBeInTheDocument();
  });
});
