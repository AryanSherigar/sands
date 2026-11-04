import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { createQueryWrapper } from "@/test/queryWrapper";
import type { CampaignWorldView } from "../../types/simulation.types";
import { useResumePendingBattleSpeech } from "../useResumePendingBattleSpeech";

const SPEECH_URL = "*/simulation/v1/playthroughs/pt-1/battles/battle_1/speech";
const speechView = (status: "pending" | "done") => ({
  status,
  officer_report: "Captain Hale: My lord, the men are steady enough, no more than that.",
  mood: { morale: "steady", exhaustion: "fresh", pay: "paid" },
  next_talk: status === "pending" ? 1 : null,
  reactions: [],
  outcome: null,
});
const battles = (controlMode: string, status = "pending") =>
  [{ id: "battle_1", control_mode: controlMode, status }] as unknown as CampaignWorldView["battles"];

const renderResume = (
  worldBattles: CampaignWorldView["battles"],
  activeBattleId: string | null,
  onResume: (battleId: string) => void,
) =>
  renderHook(
    () => useResumePendingBattleSpeech("pt-1", worldBattles, activeBattleId, onResume),
    { wrapper: createQueryWrapper() },
  );

describe("useResumePendingBattleSpeech", () => {
  it("reopens the council for a player battle whose speech is still pending", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json(speechView("pending"))));
    const onResume = vi.fn();
    renderResume(battles("player"), null, onResume);
    await waitFor(() => expect(onResume).toHaveBeenCalledWith("battle_1"));
    expect(onResume).toHaveBeenCalledTimes(1);
  });

  it("stays quiet when the speech is already done", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json(speechView("done"))));
    const onResume = vi.fn();
    renderResume(battles("player"), null, onResume);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(onResume).not.toHaveBeenCalled();
  });

  it("stays quiet when the council is already open", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json(speechView("pending"))));
    const onResume = vi.fn();
    renderResume(battles("player"), "battle_1", onResume);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(onResume).not.toHaveBeenCalled();
  });

  it("ignores battles the player is not commanding", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json(speechView("pending"))));
    const onResume = vi.fn();
    renderResume(battles("ai"), null, onResume);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(onResume).not.toHaveBeenCalled();
  });
});
