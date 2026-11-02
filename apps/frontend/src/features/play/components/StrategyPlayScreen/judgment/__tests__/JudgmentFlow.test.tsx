import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { useLiveJudgment } from "../../../../hooks/useLiveJudgment";
import { getWorldQueryKey } from "../../../../hooks/useSimulationCommands";
import type { SceneMessageCallbacks } from "../../../../lib/scene-stream";
import type { SceneViewResponse } from "../../../../types/scene.types";
import { StrategyJudgmentDialog } from "../StrategyJudgmentDialog";

const streamMock = vi.hoisted(() => ({
  start: vi.fn(),
  callbacks: null as SceneMessageCallbacks | null,
}));

vi.mock("../../../../lib/scene-stream", () => ({
  startSceneMessage: (
    sceneId: string,
    text: string,
    callbacks: SceneMessageCallbacks,
    options: unknown,
  ) => {
    streamMock.callbacks = callbacks;
    streamMock.start(sceneId, text, options);
    return vi.fn();
  },
}));

const PLAYTHROUGH = "pt-1";
const SCENE = "scene-j";
const OPENING = 'The hall is silent.\nBRANNOCH: "An open defiance requires an open reckoning."';

const baseView: SceneViewResponse = {
  scene_id: SCENE,
  scene_type: "judgment",
  status: "opened",
  turn: 5,
  initiator: "ai",
  is_declinable: false,
  situation: { summary: "Harl stands accused.", facts: [{ label: "Charge", value: "treason" }] },
  participants: [
    { participant_id: "harl", kind: "governor", name: "Harl", trait_ids: [] },
    { participant_id: "veyra", kind: "governor", name: "Veyra", trait_ids: [], stance: "mercy" },
    { participant_id: "brannoch", kind: "officer", name: "Brannoch", trait_ids: [], stance: "iron" },
  ],
  transcript: [{ sequence: 1, player_text: "", leader_text: OPENING }],
  exchanges_remaining: 5,
};

let currentView: SceneViewResponse = baseView;

function serve(view: SceneViewResponse) {
  currentView = view;
  server.use(
    http.get(`*/simulation/v1/playthroughs/${PLAYTHROUGH}/scenes/:sceneId`, () =>
      HttpResponse.json(currentView),
    ),
  );
}

const spokenView: SceneViewResponse = {
  ...baseView,
  exchanges_remaining: 4,
  transcript: [
    ...baseView.transcript,
    { sequence: 2, player_text: "Why did you rise?", leader_text: 'HARL: "Bread."' },
  ],
};

const resolvedView: SceneViewResponse = {
  ...baseView,
  status: "resolved",
  exchanges_remaining: 0,
  outcome: { kind: "judgment", verdict: "exile", nuance: "beyond_border" },
  outcome_summary: [
    "Judgment: Exiled (beyond border).",
    "The governor is removed from their post.",
    "Your other governors' regard: -2 (they watched this judgment).",
  ],
};

function Harness() {
  const judgment = useLiveJudgment(PLAYTHROUGH, { status: "awaiting_scene", scene_id: SCENE });
  if (!judgment.pkg) return <p>No judgment.</p>;
  return (
    <StrategyJudgmentDialog
      isOpen={judgment.isOpen}
      pkg={judgment.pkg}
      liveText={judgment.liveText}
      isStreaming={judgment.isStreaming}
      failureMessage={judgment.failureMessage}
      onSpeak={judgment.handleSpeak}
      onPronounce={judgment.handlePronounce}
      onDismissReveal={judgment.handleDismissReveal}
      onClose={judgment.handleClose}
    />
  );
}

function renderFlow() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(getWorldQueryKey(PLAYTHROUGH), {
    world_version: 3,
    turn: 5,
    wave: 0,
    status: "awaiting_scene",
  });
  return render(
    <QueryClientProvider client={client}>
      <Harness />
    </QueryClientProvider>,
  );
}

describe("judgment scene flow", () => {
  beforeEach(() => {
    streamMock.start.mockClear();
    streamMock.callbacks = null;
  });

  it("opens, hears the court, pronounces a verdict and sees the consequences", async () => {
    serve(baseView);
    const user = userEvent.setup();
    renderFlow();

    expect(await screen.findByText("The hall is silent.")).toBeInTheDocument();
    expect(streamMock.start).not.toHaveBeenCalled();

    await user.type(screen.getByRole("textbox"), "Why did you rise?");
    await user.click(screen.getByRole("button", { name: /^speak/i }));
    expect(streamMock.start).toHaveBeenLastCalledWith(SCENE, "Why did you rise?", {});
    serve(spokenView);
    act(() => streamMock.callbacks?.onNarration('HARL: "Bread."'));
    act(() => streamMock.callbacks?.onDone());
    expect(await screen.findByText(/Bread/)).toBeInTheDocument();

    await user.keyboard("2");
    await user.click(screen.getByRole("button", { name: "beyond the border" }));
    await user.click(screen.getByRole("button", { name: /pronounce judgment/i }));
    expect(streamMock.start).toHaveBeenLastCalledWith(SCENE, "", {
      kind: "pronounce",
      verdict: "exile",
      nuance: "beyond_border",
    });
    serve(resolvedView);
    act(() => streamMock.callbacks?.onNarration("The sentence lands."));
    act(() => streamMock.callbacks?.onDone());

    expect(await screen.findByText("Judgment: Exiled (beyond border).")).toBeInTheDocument();
    expect(screen.getByText(/-2 \(they watched this judgment\)/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /return to the realm/i }));
    await waitFor(() => expect(screen.getByText("No judgment.")).toBeInTheDocument());
  });

  it("imprisons the accused after the player confirms leaving", async () => {
    serve(baseView);
    const user = userEvent.setup();
    renderFlow();
    await screen.findByText("The hall is silent.");
    await user.click(screen.getByRole("button", { name: /exit/i }));
    await user.click(screen.getByRole("button", { name: /leave the hall/i }));
    expect(streamMock.start).toHaveBeenCalledWith(SCENE, "", {
      kind: "pronounce",
      verdict: "imprison",
    });
  });
});
