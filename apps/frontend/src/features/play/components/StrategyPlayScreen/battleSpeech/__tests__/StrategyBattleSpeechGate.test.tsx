import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@/test/msw/server";
import { useBattleSpeechStore } from "../../../../stores/battleSpeech.store";
import { StrategyBattleSpeechGate } from "../StrategyBattleSpeechGate";
import {
  BATTLE_ID,
  OFFICER_REPORT,
  PLAYTHROUGH_ID,
  makeWrapper,
  mockSpeechServer,
  stubAudioContext,
} from "./battleSpeechTestKit";

const SPEECH_URL = `*/simulation/v1/playthroughs/${PLAYTHROUGH_ID}/battles/${BATTLE_ID}/speech`;

const renderGate = () => {
  const { wrapper } = makeWrapper();
  return render(
    <StrategyBattleSpeechGate playthroughId={PLAYTHROUGH_ID} battleId={BATTLE_ID}>
      <p>War council</p>
    </StrategyBattleSpeechGate>,
    { wrapper },
  );
};

describe("StrategyBattleSpeechGate", () => {
  beforeEach(() => {
    stubAudioContext();
    useBattleSpeechStore.getState().reset();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows the speech before the war council while the speech is pending", async () => {
    mockSpeechServer();
    renderGate();
    expect(await screen.findByText(OFFICER_REPORT)).toBeInTheDocument();
    expect(screen.queryByText("War council")).not.toBeInTheDocument();
  });

  it("goes straight to the war council when the battle has no speech", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json({ detail: "none" }, { status: 404 })));
    renderGate();
    expect(await screen.findByText("War council")).toBeInTheDocument();
  });

  it("goes straight to the war council when the speech is already done", async () => {
    mockSpeechServer(3);
    renderGate();
    expect(await screen.findByText("War council")).toBeInTheDocument();
  });

  it("opens the war council if the speech cannot be loaded, so the battle is never stuck", async () => {
    server.use(http.get(SPEECH_URL, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    renderGate();
    expect(await screen.findByText("War council")).toBeInTheDocument();
  });

  it("holds the overlay on the result until the player continues", async () => {
    mockSpeechServer(3);
    useBattleSpeechStore.setState({ phase: "result" });
    renderGate();
    expect(await screen.findByRole("button", { name: /to the battle/i })).toBeInTheDocument();
    expect(screen.queryByText("War council")).not.toBeInTheDocument();
  });

  it("shows nothing while the speech is loading", () => {
    mockSpeechServer();
    renderGate();
    expect(screen.queryByText("War council")).not.toBeInTheDocument();
    expect(screen.queryByText(OFFICER_REPORT)).not.toBeInTheDocument();
  });
});
