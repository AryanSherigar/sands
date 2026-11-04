import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { vi } from "vitest";
import { FakeAudioContext } from "@/shared/lib/audio/__tests__/fakeAudioContext";
import { server } from "@/test/msw/server";
import type { CrowdReaction, SpeechView } from "../../../../types/battleSpeech.types";
import type { CampaignWorldView, MutationResponse } from "../../../../types/simulation.types";
import { DEFAULT_PREVIEW_WORLD } from "../../defaultPreviewWorld";

export const PLAYTHROUGH_ID = "pt-1";
export const BATTLE_ID = "battle_1";
export const OFFICER_REPORT = "Captain Hale: My lord, the men are shaken and keep looking back.";
export const CLOSING_MORALE_DELTA = 9;

const BASE_URL = `*/simulation/v1/playthroughs/${PLAYTHROUGH_ID}/battles/${BATTLE_ID}/speech`;
const REACTIONS: CrowdReaction[] = [
  { mood: "murmur", intensity: 1 },
  { mood: "cheer", intensity: 2 },
  { mood: "cheer", intensity: 3 },
];

const stateAfter = (worldVersion: number): MutationResponse => ({
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

export interface SpeechServerLog {
  talks: { talk_index: number; text: string }[];
  skipCount: number;
}

export function mockSpeechServer(initialTalks = 0): SpeechServerLog {
  const log: SpeechServerLog = { talks: [], skipCount: 0 };
  let given = initialTalks;
  let isSkipped = false;
  const isDone = () => given >= REACTIONS.length || isSkipped;
  const view = (): SpeechView => ({
    status: isDone() ? "done" : "pending",
    officer_report: OFFICER_REPORT,
    mood: { morale: "shaken", exhaustion: "spent", pay: "grumbling" },
    next_talk: isDone() ? null : ((given + 1) as 1 | 2 | 3),
    reactions: REACTIONS.slice(0, given),
    outcome: isDone()
      ? { kind: "battle_speech", morale_delta_percent: CLOSING_MORALE_DELTA, rubric_scores: {} }
      : null,
  });
  server.use(
    http.get(BASE_URL, () => HttpResponse.json(view())),
    http.post(`${BASE_URL}/talks`, async ({ request }) => {
      const body = (await request.json()) as { talk_index: number; text: string };
      log.talks.push({ talk_index: body.talk_index, text: body.text });
      given += 1;
      return HttpResponse.json({
        reaction: REACTIONS[given - 1],
        is_complete: isDone(),
        morale_delta_percent: isDone() ? CLOSING_MORALE_DELTA : null,
        state: stateAfter(given + 1),
      });
    }),
    http.post(`${BASE_URL}/skip`, () => {
      log.skipCount += 1;
      isSkipped = true;
      return HttpResponse.json({
        reaction: REACTIONS[0],
        is_complete: true,
        morale_delta_percent: 0,
        state: stateAfter(2),
      });
    }),
  );
  return log;
}

export function stubAudioContext(): void {
  FakeAudioContext.instances = [];
  vi.stubGlobal("AudioContext", FakeAudioContext);
}

export function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const world: CampaignWorldView = {
    ...DEFAULT_PREVIEW_WORLD,
    world_version: 1,
    turn: 1,
    wave: 0,
    status: "awaiting_commands",
  };
  queryClient.setQueryData(["simulation-world", PLAYTHROUGH_ID], world);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { wrapper, queryClient };
}
