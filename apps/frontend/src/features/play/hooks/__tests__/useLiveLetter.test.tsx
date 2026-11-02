import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import type { SceneMessageCallbacks } from "../../lib/scene-stream";
import { useStrategyPlayStore } from "../../stores/strategyPlay.store";
import { getWorldQueryKey } from "../useSimulationCommands";
import type { SceneViewResponse } from "../../types/scene.types";
import { useLiveLetter } from "../useLiveLetter";

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

const LETTER_TEXT = "Valdren, the river fords are watched.\n\nKeep your riders home.";
const PLAYTHROUGH = "pt-1";
const SCENE = "scene-letter";

const letterView = (overrides: Partial<SceneViewResponse> = {}): SceneViewResponse => ({
  scene_id: SCENE,
  scene_type: "letter",
  status: "pending",
  turn: 4,
  initiator: "ai",
  is_declinable: true,
  situation: { summary: "Mira writes.", facts: [{ label: "Topic", value: "warning" }] },
  participants: [
    { participant_id: "mira", kind: "leader", name: "Mira of Ashford", trait_ids: [] },
  ],
  transcript: [],
  exchanges_remaining: 2,
  ...overrides,
});

const storedLetter = {
  sequence: 1,
  player_text: "",
  leader_text: LETTER_TEXT,
};

let viewResponses: SceneViewResponse[] = [];
let viewRequests = 0;

function serveViews(...views: SceneViewResponse[]) {
  viewResponses = views;
  viewRequests = 0;
  server.use(
    http.get(`*/simulation/v1/playthroughs/${PLAYTHROUGH}/scenes/:sceneId`, () => {
      const index = Math.min(viewRequests, viewResponses.length - 1);
      viewRequests += 1;
      return HttpResponse.json(viewResponses[index]);
    }),
  );
}

const awaitingWorld = { status: "awaiting_scene" as const, scene_id: SCENE };
const planningWorld = { status: "planning" as const, scene_id: null };

const CACHED_WORLD = { world_version: 3, turn: 4, wave: 0, status: "awaiting_scene" };

function setup(world: { status: "awaiting_scene" | "planning"; scene_id: string | null }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(getWorldQueryKey(PLAYTHROUGH), CACHED_WORLD);
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return renderHook(() => useLiveLetter(PLAYTHROUGH, world), { wrapper });
}

describe("useLiveLetter", () => {
  beforeEach(() => {
    streamMock.start.mockClear();
    streamMock.callbacks = null;
    useStrategyPlayStore.getState().reset();
  });

  it("opens the letter from the real scene when none is stored, then shows it", async () => {
    serveViews(letterView(), letterView({ transcript: [storedLetter] }));
    const { result } = setup(awaitingWorld);

    await waitFor(() =>
      expect(streamMock.start).toHaveBeenCalledWith(SCENE, "", { kind: "open" }),
    );
    act(() => streamMock.callbacks?.onNarration("Valdren, the river fords are watched."));
    act(() => streamMock.callbacks?.onDone());

    await waitFor(() => expect(result.current.pkg?.incoming.paragraphs).toEqual([
      "Valdren, the river fords are watched.",
      "Keep your riders home.",
    ]));
    expect(result.current.pkg?.provenance.senderName).toBe("Mira of Ashford");
    expect(result.current.isOpen).toBe(true);
  });

  it("shows a stored letter after a reload without asking the model again", async () => {
    serveViews(letterView({ status: "opened", transcript: [storedLetter] }));
    const { result } = setup(awaitingWorld);

    await waitFor(() => expect(result.current.pkg).not.toBeNull());
    expect(streamMock.start).not.toHaveBeenCalled();
    expect(result.current.isOpen).toBe(true);
  });

  it("ignores scenes that are not letters and reports the type as resolved", async () => {
    serveViews(letterView({ scene_type: "negotiation" }));
    const { result } = setup(awaitingWorld);

    await waitFor(() => expect(result.current.isSceneTypeResolved).toBe(true));
    expect(result.current.isLetterScene).toBe(false);
    expect(result.current.pkg).toBeNull();
    expect(streamMock.start).not.toHaveBeenCalled();
  });

  it("is inert when the world is not waiting on a scene", () => {
    serveViews(letterView());
    const { result } = setup(planningWorld);

    expect(result.current.isLetterScene).toBe(false);
    expect(result.current.isSceneTypeResolved).toBe(true);
    expect(viewRequests).toBe(0);
  });

  it("shelves the letter on close and reopens it from the shelf", async () => {
    serveViews(letterView({ status: "opened", transcript: [storedLetter] }));
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.isOpen).toBe(true));
    expect(result.current.dispatchNumber).toBeUndefined();

    act(() => result.current.handleClose());
    expect(result.current.isOpen).toBe(false);
    expect(result.current.dispatchNumber).toBe(4);

    act(() => result.current.handleOpen());
    expect(result.current.isOpen).toBe(true);
  });

  it("seals the real prose and reports the outcome in words", async () => {
    serveViews(
      letterView({ status: "opened", transcript: [storedLetter] }),
      letterView({
        status: "resolved",
        transcript: [storedLetter],
        outcome: { kind: "choice", option_id: "letter_warmer" },
        exchanges_remaining: 0,
      }),
    );
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());

    let sealed: Promise<boolean | void> | undefined;
    act(() => {
      sealed = Promise.resolve(
        result.current.handleSeal({
          sceneId: SCENE,
          finalProse: "Our bailiffs will walk the line.",
          revisionCount: 1,
        }),
      );
    });
    expect(streamMock.start).toHaveBeenCalledWith(
      SCENE,
      "Our bailiffs will walk the line.",
      { kind: "seal" },
    );
    act(() => streamMock.callbacks?.onDone());

    await expect(sealed).resolves.toBe(true);
    expect(useStrategyPlayStore.getState().orderFeedback?.message).toBe(
      "Your reply warmed their regard for you.",
    );
  });

  it("keeps the letter and says nothing when the seal fails", async () => {
    serveViews(letterView({ status: "opened", transcript: [storedLetter] }));
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());

    let sealed: Promise<boolean | void> | undefined;
    act(() => {
      sealed = Promise.resolve(
        result.current.handleSeal({ sceneId: SCENE, finalProse: "Prose", revisionCount: 1 }),
      );
    });
    act(() => streamMock.callbacks?.onFailure("Connection lost."));

    await expect(sealed).resolves.toBe(false);
    expect(useStrategyPlayStore.getState().orderFeedback).toBeNull();
  });

  it("declines the letter with an unconfirmed decision and says it was left unanswered", async () => {
    serveViews(letterView({ status: "opened", transcript: [storedLetter] }));
    const decisions: Array<Record<string, unknown>> = [];
    server.use(
      http.post(
        `*/simulation/v1/playthroughs/${PLAYTHROUGH}/scenes/${SCENE}/decision`,
        async ({ request }) => {
          decisions.push((await request.json()) as Record<string, unknown>);
          return HttpResponse.json({ world_version: 4 });
        },
      ),
    );
    const { result } = setup(awaitingWorld);
    await waitFor(() => expect(result.current.pkg).not.toBeNull());

    act(() => result.current.handleDecline());

    await waitFor(() => expect(decisions).toHaveLength(1));
    expect(decisions[0]).toMatchObject({ is_confirmed: false, expected_world_version: 3 });
    await waitFor(() =>
      expect(useStrategyPlayStore.getState().orderFeedback?.message).toBe(
        "You left the letter unanswered.",
      ),
    );
  });
});
