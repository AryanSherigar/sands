import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { server } from "@/test/msw/server";
import { StrategyPlayScreen } from "../StrategyPlayScreen";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import { DEFAULT_PREVIEW_WORLD } from "../../StrategyPlayScreen/defaultPreviewWorld";
import type { SceneViewResponse, TermsCard } from "../../../types/scene.types";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "p1" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({ data: null, isLoading: false, isError: false }),
}));

vi.mock("../../../lib/scene-stream", () => ({
  startSceneMessage: vi.fn(() => vi.fn()),
}));

const BASE = "*/simulation/v1/playthroughs/p1";
const SCENE_ID = "scene-offer";
const SETTLE_MS = 300;
const CARD: TermsCard = {
  proposer_id: "house_carrow",
  counterpart_id: "house_ashford",
  terms: [
    { kind: "non_aggression", faction_a: "house_carrow", faction_b: "house_ashford", duration_turns: 8 },
  ],
  is_confirmed_by_player: false,
  is_confirmed_by_counterpart: true,
};

interface Backend {
  world: Record<string, unknown>;
  scene: SceneViewResponse;
  decisionBody: Record<string, unknown> | null;
}

function worldAt(status: string, turn: number, sceneId: string | null) {
  return {
    ...DEFAULT_PREVIEW_WORLD,
    world_version: turn * 10,
    turn,
    wave: 0,
    status,
    scene_id: sceneId,
    clock: { ...DEFAULT_PREVIEW_WORLD.clock, turn },
  };
}

function offerScene(overrides: Partial<SceneViewResponse> = {}): SceneViewResponse {
  return {
    scene_id: SCENE_ID,
    scene_type: "negotiation",
    status: "opened",
    turn: 2,
    initiator: "ai",
    is_declinable: false,
    situation: { summary: "Mira approaches you with an offer of a non-aggression pact.", facts: [] },
    participants: [{ participant_id: "mira", kind: "leader", name: "Mira of Ashford", trait_ids: [] }],
    transcript: [{ sequence: 1, player_text: "Speak.", leader_text: "Eight turns." }],
    exchanges_remaining: 5,
    pending_proposal: CARD,
    pending_proposal_sequence: 1,
    outcome: null,
    ...overrides,
  };
}

function installBackend(): Backend {
  const backend: Backend = {
    world: worldAt("planning", 1, null),
    scene: offerScene(),
    decisionBody: null,
  };
  server.use(
    http.get(`${BASE}/world`, () => HttpResponse.json(backend.world)),
    http.post(`${BASE}/end-turn`, () => {
      backend.world = worldAt("awaiting_scene", 2, SCENE_ID);
      return HttpResponse.json({
        playthrough_id: "p1",
        world_version: 20,
        world_hash: "h",
        turn: 2,
        wave: 0,
        orders_remaining: 4,
        status: "turn_completed",
        battles: [],
        scene_id: SCENE_ID,
        operation_id: "end",
      });
    }),
    http.get(`${BASE}/turns/:turn/report`, () => new HttpResponse(null, { status: 404 })),
    http.get(`${BASE}/scenes/${SCENE_ID}`, () => HttpResponse.json(backend.scene)),
    http.post(`${BASE}/scenes/${SCENE_ID}/decision`, async ({ request }) => {
      backend.decisionBody = (await request.json()) as Record<string, unknown>;
      backend.world = worldAt("planning", 2, null);
      backend.scene = offerScene({
        status: "resolved",
        pending_proposal: null,
        pending_proposal_sequence: null,
        outcome: {
          kind: "terms_card",
          result: "agreed",
          terms_card: { ...CARD, is_confirmed_by_player: true },
        },
      });
      return HttpResponse.json({ status: "planning" });
    }),
  );
  return backend;
}

function renderScreen() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <StrategyPlayScreen />
    </QueryClientProvider>,
  );
}

describe("StrategyPlayScreen negotiation flow", () => {
  beforeEach(() => {
    useStrategyPlayStore.getState().reset();
  });

  it("opens a triggered offer after End Turn, signs it, and returns to planning", async () => {
    const backend = installBackend();
    renderScreen();

    fireEvent.click(await screen.findByRole("button", { name: /^end turn advances/i }));
    const confirmPrompt = await screen.findByRole("alertdialog", { name: "Confirm end turn" });
    fireEvent.click(within(confirmPrompt).getByRole("button", { name: "End turn" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Incoming offer")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Decline" })).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Sign the pact" }));
    await waitFor(() => expect(backend.decisionBody).not.toBeNull());
    expect(backend.decisionBody).toMatchObject({ is_confirmed: true, proposal_sequence: 1 });

    expect(await within(dialog).findByRole("status")).toHaveTextContent("The pact is sealed.");
    fireEvent.click(within(dialog).getAllByRole("button", { name: "Close" })[0]);

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^end turn advances/i })).toBeEnabled();
  });

  it("reopens a pending offer after a refresh", async () => {
    const backend = installBackend();
    backend.world = worldAt("awaiting_scene", 2, SCENE_ID);
    renderScreen();
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Incoming offer")).toBeInTheDocument();
  });
});
