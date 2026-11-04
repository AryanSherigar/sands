import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { DEFAULT_PREVIEW_WORLD } from "../../components/StrategyPlayScreen/defaultPreviewWorld";
import type { MutationResponse } from "../../types/simulation.types";
import { useBattleSpeechStore } from "../../stores/battleSpeech.store";
import { useSubmitSpeechTalk } from "../useSubmitSpeechTalk";

const PLAYTHROUGH_ID = "pt-1";
const BATTLE_ID = "battle_1";
const TALKS_URL = `*/simulation/v1/playthroughs/${PLAYTHROUGH_ID}/battles/${BATTLE_ID}/speech/talks`;

const state = (worldVersion: number): MutationResponse => ({
  playthrough_id: PLAYTHROUGH_ID,
  world_version: worldVersion,
  world_hash: "hash",
  turn: 1,
  wave: 0,
  orders_remaining: 0,
  status: "awaiting_commands",
  battles: [],
  operation_id: "op",
});

function renderSubmit() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  queryClient.setQueryData(["simulation-world", PLAYTHROUGH_ID], {
    ...DEFAULT_PREVIEW_WORLD,
    world_version: 1,
    turn: 1,
    wave: 0,
    status: "awaiting_commands",
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, ...renderHook(() => useSubmitSpeechTalk(PLAYTHROUGH_ID, BATTLE_ID), { wrapper }) };
}

describe("useSubmitSpeechTalk", () => {
  it("sends a guarded talk, shows the reaction and keeps the world version moving", async () => {
    useBattleSpeechStore.getState().reset();
    let body: Record<string, unknown> = {};
    server.use(
      http.post(TALKS_URL, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          reaction: { mood: "cheer", intensity: 2 },
          is_complete: false,
          morale_delta_percent: null,
          state: state(2),
        });
      }),
    );
    const { result, queryClient } = renderSubmit();
    act(() => result.current.submitTalk({ talkIndex: 1, text: "Stand with me." }));
    await waitFor(() => expect(useBattleSpeechStore.getState().phase).toBe("reacting"));
    expect(body.talk_index).toBe(1);
    expect(body.text).toBe("Stand with me.");
    expect(body.guard).toMatchObject({ expected_world_version: 1, expected_turn: 1, expected_wave: 1 });
    expect(useBattleSpeechStore.getState().lastReaction).toEqual({ mood: "cheer", intensity: 2 });
    const cached = queryClient.getQueryData<{ world_version: number }>(["simulation-world", PLAYTHROUGH_ID]);
    expect(cached?.world_version).toBe(2);
  });

  it("goes to the result when the closing talk completes the speech", async () => {
    useBattleSpeechStore.getState().reset();
    server.use(
      http.post(TALKS_URL, () =>
        HttpResponse.json({
          reaction: { mood: "protest", intensity: 3 },
          is_complete: true,
          morale_delta_percent: -9,
          state: state(4),
        }),
      ),
    );
    const { result } = renderSubmit();
    act(() => result.current.submitTalk({ talkIndex: 3, text: "Forward!" }));
    await waitFor(() => expect(result.current.result?.morale_delta_percent).toBe(-9));
    expect(useBattleSpeechStore.getState().phase).toBe("reacting");
    act(() => useBattleSpeechStore.getState().continueAfterReaction(true));
    expect(useBattleSpeechStore.getState().phase).toBe("result");
  });

  it("keeps the phase and reports the error when the server refuses the talk", async () => {
    useBattleSpeechStore.getState().reset();
    useBattleSpeechStore.getState().beginTalking();
    server.use(
      http.post(TALKS_URL, () => HttpResponse.json({ detail: "talk out of order" }, { status: 409 })),
    );
    const { result } = renderSubmit();
    act(() => result.current.submitTalk({ talkIndex: 2, text: "Too soon." }));
    await waitFor(() => expect(result.current.errorInfo?.status).toBe(409));
    expect(useBattleSpeechStore.getState().phase).toBe("talking");
  });
});
