import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import type { SceneMessageCallbacks } from "../../lib/scene-stream";
import type { SceneViewResponse } from "../../types/scene.types";
import { getWorldQueryKey } from "../useSimulationCommands";
import { useLiveJudgment } from "../useLiveJudgment";

const streamMock = vi.hoisted(() => ({
  start: vi.fn(),
  callbacks: null as SceneMessageCallbacks | null,
}));

vi.mock("../../lib/scene-stream", () => ({
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
const OPENING = "The hall is silent.";

const judgmentView = (overrides: Partial<SceneViewResponse> = {}): SceneViewResponse => ({
  scene_id: SCENE,
  scene_type: "judgment",
  status: "pending",
  turn: 5,
  initiator: "ai",
  is_declinable: false,
  situation: { summary: "Harl stands accused.", facts: [{ label: "Charge", value: "treason" }] },
  participants: [
    { participant_id: "harl", kind: "governor", name: "Harl", trait_ids: [] },
    { participant_id: "veyra", kind: "governor", name: "Veyra", trait_ids: [], stance: "mercy" },
  ],
  transcript: [],
  exchanges_remaining: 6,
  ...overrides,
});

const opened = { sequence: 1, player_text: "", leader_text: OPENING };

let responses: SceneViewResponse[] = [];
let requests = 0;

function serveViews(...views: SceneViewResponse[]) {
  responses = views;
  requests = 0;
  server.use(
    http.get(`*/simulation/v1/playthroughs/${PLAYTHROUGH}/scenes/:sceneId`, () => {
      const index = Math.min(requests, responses.length - 1);
      requests += 1;
      return HttpResponse.json(responses[index]);
    }),
  );
}

const awaitingWorld = { status: "awaiting_scene" as const, scene_id: SCENE };
const planningWorld = { status: "planning" as const, scene_id: null };

function setup(world: { status: "awaiting_scene" | "planning"; scene_id: string | null }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(getWorldQueryKey(PLAYTHROUGH), {
    world_version: 3,
    turn: 5,
    wave: 0,
    status: "awaiting_scene",
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return renderHook(() => useLiveJudgment(PLAYTHROUGH, world), { wrapper });
}

describe("useLiveJudgment", () => {
  beforeEach(() => {
    streamMock.start.mockClear();
    streamMock.callbacks = null;
  });

  it("is closed and makes no request when the world is not waiting on a scene", () => {
    serveViews(judgmentView());
    const { result } = setup(planningWorld);
    expect(result.current.pkg).toBeNull();
    expect(result.current.isJudgmentScene).toBe(false);
    expect(result.current.isSceneTypeResolved).toBe(true);
    expect(requests).toBe(0);
  });

  it("ignores scenes that are not judgments", async () => {
    serveViews(judgmentView({ scene_type: "negotiation" }));
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.isSceneTypeResolved).toBe(true));
    expect(result.current.isJudgmentScene).toBe(false);
    expect(streamMock.start).not.toHaveBeenCalled();
  });

  it("convenes the court once when none is stored, then shows the tableau", async () => {
    serveViews(judgmentView(), judgmentView({ transcript: [opened], exchanges_remaining: 5 }));
    const { result } = setup(awaitingWorld);
    await waitFor(() =>
      expect(streamMock.start).toHaveBeenCalledWith(SCENE, "", { kind: "open" }),
    );
    act(() => streamMock.callbacks?.onNarration(OPENING));
    act(() => streamMock.callbacks?.onDone());
    await waitFor(() => expect(result.current.pkg?.openingText).toBe(OPENING));
    expect(result.current.isOpen).toBe(true);
    expect(streamMock.start).toHaveBeenCalledTimes(1);
  });

  it("shows a stored tableau after a reload without asking the model again", async () => {
    serveViews(judgmentView({ status: "opened", transcript: [opened], exchanges_remaining: 5 }));
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());
    expect(streamMock.start).not.toHaveBeenCalled();
  });

  it("speaks to the court as a plain message", async () => {
    serveViews(judgmentView({ status: "opened", transcript: [opened], exchanges_remaining: 5 }));
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());
    act(() => {
      void result.current.handleSpeak("Why did you rise?");
    });
    expect(streamMock.start).toHaveBeenCalledWith(SCENE, "Why did you rise?", {});
  });

  it("pronounces the verdict and keeps the dialog open to reveal the consequences", async () => {
    serveViews(
      judgmentView({ status: "opened", transcript: [opened], exchanges_remaining: 5 }),
      judgmentView({
        status: "resolved",
        transcript: [opened],
        outcome: { kind: "judgment", verdict: "execute", nuance: "publicly" },
        outcome_summary: ["Judgment: Executed (publicly)."],
        exchanges_remaining: 0,
      }),
    );
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());
    let pronounced: Promise<boolean> | undefined;
    act(() => {
      pronounced = result.current.handlePronounce({
        verdict: "execute",
        nuance: "publicly",
        decreeText: "Let it be seen.",
      });
    });
    expect(streamMock.start).toHaveBeenCalledWith(SCENE, "Let it be seen.", {
      kind: "pronounce",
      verdict: "execute",
      nuance: "publicly",
    });
    act(() => streamMock.callbacks?.onDone());
    await expect(pronounced).resolves.toBe(true);
    await waitFor(() => expect(result.current.pkg?.isResolved).toBe(true));
    expect(result.current.pkg?.outcomeSummary).toEqual(["Judgment: Executed (publicly)."]);
    expect(result.current.isOpen).toBe(true);
    act(() => result.current.handleDismissReveal());
    expect(result.current.isOpen).toBe(false);
  });

  it("pronounces imprisonment when the player leaves", async () => {
    serveViews(judgmentView({ status: "opened", transcript: [opened], exchanges_remaining: 5 }));
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());
    act(() => result.current.handleClose());
    expect(streamMock.start).toHaveBeenCalledWith(SCENE, "", {
      kind: "pronounce",
      verdict: "imprison",
    });
  });
});
