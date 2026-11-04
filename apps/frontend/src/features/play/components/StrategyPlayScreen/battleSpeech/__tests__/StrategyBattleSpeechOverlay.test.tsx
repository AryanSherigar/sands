import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useBattleSpeechStore } from "../../../../stores/battleSpeech.store";
import { StrategyBattleSpeechOverlay } from "../StrategyBattleSpeechOverlay";
import {
  BATTLE_ID,
  OFFICER_REPORT,
  PLAYTHROUGH_ID,
  makeWrapper,
  mockSpeechServer,
  stubAudioContext,
} from "./battleSpeechTestKit";

const renderOverlay = () => {
  const { wrapper } = makeWrapper();
  return render(
    <StrategyBattleSpeechOverlay playthroughId={PLAYTHROUGH_ID} battleId={BATTLE_ID} />,
    { wrapper },
  );
};

async function giveTalk(text: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByRole("textbox", { name: /your talk/i }), text);
  await user.click(screen.getByRole("button", { name: /^deliver/i }));
}

describe("StrategyBattleSpeechOverlay", () => {
  beforeEach(() => {
    stubAudioContext();
    useBattleSpeechStore.getState().reset();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("opens with the officer's informal report and no numbers", async () => {
    mockSpeechServer();
    renderOverlay();
    expect(await screen.findByText(OFFICER_REPORT)).toBeInTheDocument();
    expect(screen.queryByText(/morale/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\d+\s*%/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /step forward/i })).toBeInTheDocument();
  });

  it("lets the player give three typed talks, each followed by a reaction", async () => {
    const log = mockSpeechServer();
    const user = userEvent.setup();
    renderOverlay();
    await user.click(await screen.findByRole("button", { name: /step forward/i }));
    expect(await screen.findByText(/opening talk/i)).toBeInTheDocument();
    await giveTalk("We hold the line.");
    expect(await screen.findByText(/a low murmur/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /continue/i }));
    expect(await screen.findByText(/middle talk/i)).toBeInTheDocument();
    await giveTalk("Think of home.");
    expect(await screen.findByText(/the crowd cheers/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /continue/i }));
    expect(await screen.findByText(/closing talk/i)).toBeInTheDocument();
    expect(log.talks.map((talk) => talk.talk_index)).toEqual([1, 2]);
  });

  it("shows the morale result only after the closing talk", async () => {
    const log = mockSpeechServer(2);
    const user = userEvent.setup();
    useBattleSpeechStore.getState().beginTalking();
    renderOverlay();
    await giveTalk("Now, forward!");
    await user.click(await screen.findByRole("button", { name: /continue/i }));
    expect(await screen.findByText(/morale rose by 9/i)).toBeInTheDocument();
    expect(log.talks).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: /to the battle/i }));
    expect(useBattleSpeechStore.getState().phase).toBe("report");
  });

  it("does not deliver an empty talk", async () => {
    const log = mockSpeechServer();
    const user = userEvent.setup();
    useBattleSpeechStore.getState().beginTalking();
    renderOverlay();
    await screen.findByRole("textbox", { name: /your talk/i });
    expect(screen.getByRole("button", { name: /^deliver/i })).toBeDisabled();
    await user.type(screen.getByRole("textbox", { name: /your talk/i }), "   ");
    expect(screen.getByRole("button", { name: /^deliver/i })).toBeDisabled();
    expect(log.talks).toHaveLength(0);
  });

  it("lets the player skip the speech", async () => {
    const log = mockSpeechServer();
    const user = userEvent.setup();
    renderOverlay();
    await user.click(await screen.findByRole("button", { name: /skip the speech/i }));
    await vi.waitFor(() => expect(log.skipCount).toBe(1));
  });

  it("falls back to typing when the browser cannot record", async () => {
    mockSpeechServer();
    useBattleSpeechStore.getState().beginTalking();
    renderOverlay();
    await screen.findByRole("textbox", { name: /your talk/i });
    expect(screen.queryByRole("button", { name: /hold to speak/i })).not.toBeInTheDocument();
    expect(screen.getByText(/voice input isn't available/i)).toBeInTheDocument();
  });
});
