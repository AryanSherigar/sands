import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { usePlayStore } from "../../../../stores/play.store";
import { TurnLogItem } from "../../../../types/play.types";
import { EBookTurnEntry } from "../EBookTurnEntry";

const mockIsVoiceOutputEnabled = vi.fn();
vi.mock("@/shared/hooks/useVoiceOutputPreference", () => ({
  useVoiceOutputPreference: () => ({
    isVoiceOutputEnabled: mockIsVoiceOutputEnabled(),
  }),
}));

vi.mock("../../NarrationFlag/NarrationFlag", () => ({
  NarrationFlag: () => null,
}));

const mockTurn: TurnLogItem = {
  id: "turn-1",
  turn_number: 1,
  action_mode: "do",
  action_text: "I inspect the ancient altar.",
  narration_text:
    "Dust falls from the ceiling as shadows flicker across the stones.",
  created_at: new Date().toISOString(),
};

describe("EBookTurnEntry — narration font application", () => {
  beforeEach(() => {
    usePlayStore.setState({
      reader_font_override: null,
      playthrough: null,
    });
  });

  it("applies default narration font class to narration paragraphs", () => {
    render(
      <EBookTurnEntry
        turn={mockTurn}
        turnIndex={0}
        isLatest={true}
      />,
    );

    const paragraph = screen.getByText(/dust falls from the ceiling/i);
    expect(paragraph).toHaveClass("font-narration-arial");

    const actionQuote = screen.getByText(/"I inspect the ancient altar."/i);
    expect(actionQuote).not.toHaveClass("font-narration-arial");
    expect(actionQuote).toHaveClass("font-serif");
  });

  it("applies reader font override class to narration paragraphs when set", () => {
    usePlayStore.setState({
      reader_font_override: "special-elite",
    });

    render(
      <EBookTurnEntry
        turn={mockTurn}
        turnIndex={0}
        isLatest={true}
      />,
    );

    const paragraph = screen.getByText(/dust falls from the ceiling/i);
    expect(paragraph).toHaveClass("font-narration-special-elite");
  });
});

describe("EBookTurnEntry — narration audio play button", () => {
  const turnWithAudio: TurnLogItem = {
    ...mockTurn,
    audio_url: "https://storage.googleapis.com/fake-bucket/narration-audio/1.wav",
  };

  beforeEach(() => {
    usePlayStore.setState({
      reader_font_override: null,
      playthrough: null,
      playing_audio_turn_id: null,
    });
    mockIsVoiceOutputEnabled.mockReturnValue(true);
    vi.spyOn(HTMLMediaElement.prototype, "play").mockReturnValue(
      Promise.resolve(),
    );
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  });

  it("does not render when the turn has no audio_url", () => {
    render(
      <EBookTurnEntry
        turn={mockTurn}
        turnIndex={0}
        isLatest={true}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /play narration/i }),
    ).not.toBeInTheDocument();
  });

  it("does not render when voice output is disabled, even with an audio_url", () => {
    mockIsVoiceOutputEnabled.mockReturnValue(false);

    render(
      <EBookTurnEntry
        turn={turnWithAudio}
        turnIndex={0}
        isLatest={true}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /play narration/i }),
    ).not.toBeInTheDocument();
  });

  it("renders and toggles play/stop when clicked", async () => {
    const user = userEvent.setup();
    render(
      <EBookTurnEntry
        turn={turnWithAudio}
        turnIndex={0}
        isLatest={true}
      />,
    );

    const playButton = await screen.findByRole("button", {
      name: /play narration/i,
    });
    await user.click(playButton);

    expect(usePlayStore.getState().playing_audio_turn_id).toBe(turnWithAudio.id);
    expect(
      await screen.findByRole("button", { name: /stop narration/i }),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /stop narration/i }),
    );
    expect(usePlayStore.getState().playing_audio_turn_id).toBeNull();
  });
});
