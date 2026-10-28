import { beforeEach, describe, expect, it, vi } from "vitest";
import { SSEHandlers } from "@/shared/lib/sse-client";
import { PlaythroughData } from "../../types/play.types";
import { usePlayStore } from "../play.store";

let capturedHandlers: SSEHandlers | null = null;

vi.mock("@/shared/lib/sse-client", () => ({
  createPostSSEConnection: (
    _url: string,
    _body: Record<string, unknown>,
    _token: string | null,
    handlers: SSEHandlers,
  ) => {
    capturedHandlers = handlers;
    return vi.fn();
  },
}));

vi.mock("@/shared/api/playthroughs.api", () => ({ getPlaythrough: vi.fn() }));

const transitionTo = vi.fn();
vi.mock("@/shared/lib/audio/ambient-soundtrack", () => ({
  ambientSoundtrack: {
    transitionTo: (...args: unknown[]) => transitionTo(...args),
    onMoodChange: vi.fn(),
    stop: vi.fn(),
    getVolume: () => 0.6,
    getIsMuted: () => false,
  },
}));

const TRACKS = { tension: "https://tracks.test/tension.mp3" };

const moodMapHints = {
  meters: [],
  tier: {
    path: "tension_tier",
    hint: { kind: "tier" as const, label: "Tension", mood_map: { tense: "tension" } },
    options: ["uneasy", "tense"],
  },
};

const setPlaythrough = (overrides: Partial<PlaythroughData>): void => {
  usePlayStore.setState({
    playthrough: {
      playthrough_id: "pt-1",
      mode: "master",
      is_spectator: false,
      participant_id: "participant-1",
      can_act: true,
      character_name: "Adventurer",
      pending_minigame: null,
      pending_check: null,
      pending_rule_check: null,
      enabled_tools: [],
      music_tracks: TRACKS,
      turns: [],
      state: {},
      hud_hints: { meters: [] },
      ...overrides,
    } as unknown as PlaythroughData,
    streaming_text: "",
    is_narrating: false,
  });
};

const sendNarratorMood = (): void => {
  usePlayStore.getState().submitTurn("I wait.");
  capturedHandlers!.onEvent("mood", "tension");
};

describe("narrator mood events and the tension tier", () => {
  beforeEach(() => {
    capturedHandlers = null;
    transitionTo.mockClear();
  });

  it("follows the narrator's mood when the scenario has no mood_map", () => {
    setPlaythrough({ enabled_tools: ["status_hud", "atmosphere"] });

    sendNarratorMood();

    expect(transitionTo).toHaveBeenCalledWith("tension", TRACKS.tension);
  });

  it("follows the narrator's mood when no tool is on", () => {
    setPlaythrough({ hud_hints: moodMapHints });

    sendNarratorMood();

    expect(transitionTo).toHaveBeenCalledTimes(1);
  });

  it("ignores the narrator's mood while a tier mood_map is active", () => {
    setPlaythrough({
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: moodMapHints,
    });

    sendNarratorMood();

    expect(transitionTo).not.toHaveBeenCalled();
  });

  it("still records the narrator's mood in the store while ignoring the audio", () => {
    setPlaythrough({
      enabled_tools: ["status_hud", "atmosphere"],
      hud_hints: moodMapHints,
    });

    sendNarratorMood();

    expect(usePlayStore.getState().is_narrating).toBe(true);
  });
});
