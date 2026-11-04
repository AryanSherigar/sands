import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import { useBattleSpeech } from "../useBattleSpeech";

const SPEECH_URL = "*/simulation/v1/playthroughs/pt-1/battles/battle_1/speech";
const VIEW = {
  status: "pending",
  officer_report: "Captain Hale: My lord, the men are steady enough, no more than that.",
  mood: { morale: "steady", exhaustion: "fresh", pay: "paid" },
  next_talk: 1,
  reactions: [],
  outcome: null,
};

describe("useBattleSpeech", () => {
  it("loads the speech view", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json(VIEW)));
    const { result } = renderHook(() => useBattleSpeech("pt-1", "battle_1"), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.speech?.next_talk).toBe(1);
    expect(result.current.isUnavailable).toBe(false);
  });

  it("reports the speech as unavailable when the battle has none", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json({ detail: "speech unavailable" }, { status: 404 })));
    const { result } = renderHook(() => useBattleSpeech("pt-1", "battle_1"), {
      wrapper: createQueryWrapper(),
    });
    await waitFor(() => expect(result.current.isUnavailable).toBe(true));
    expect(result.current.speech).toBeUndefined();
  });

  it("does not fetch without a battle id", () => {
    const { result } = renderHook(() => useBattleSpeech("pt-1", null), {
      wrapper: createQueryWrapper(),
    });
    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isUnavailable).toBe(false);
  });
});
