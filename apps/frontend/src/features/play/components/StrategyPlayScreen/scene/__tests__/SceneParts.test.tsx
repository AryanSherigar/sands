import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { SceneComposer } from "../SceneComposer";
import { SceneOutcomeBanner } from "../SceneOutcomeBanner";
import { SceneTermsCard } from "../SceneTermsCard";
import { SceneTranscript } from "../SceneTranscript";
import type { TermsCard } from "../../../../types/scene.types";

const CARD: TermsCard = {
  proposer_id: "house_carrow",
  counterpart_id: "house_ashford",
  terms: [
    {
      kind: "non_aggression",
      faction_a: "house_carrow",
      faction_b: "house_ashford",
      duration_turns: 8,
    },
  ],
  is_confirmed_by_player: false,
  is_confirmed_by_counterpart: true,
};

describe("SceneComposer", () => {
  it("sends the trimmed text on Enter and clears the box", () => {
    const onSend = vi.fn();
    render(<SceneComposer isDisabled={false} exchangesRemaining={4} onSend={onSend} />);
    const box = screen.getByLabelText("Your words");
    fireEvent.change(box, { target: { value: "  Let us make peace.  " } });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("Let us make peace.");
    expect(box).toHaveValue("");
  });

  it("keeps Shift+Enter for new lines and ignores empty input", () => {
    const onSend = vi.fn();
    render(<SceneComposer isDisabled={false} exchangesRemaining={4} onSend={onSend} />);
    const box = screen.getByLabelText("Your words");
    fireEvent.keyDown(box, { key: "Enter" });
    fireEvent.change(box, { target: { value: "hello" } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Speak" })).toBeEnabled();
  });

  it("disables input while busy and reports exchanges left", () => {
    render(<SceneComposer isDisabled exchangesRemaining={1} onSend={vi.fn()} />);
    expect(screen.getByLabelText("Your words")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Speak" })).toBeDisabled();
    expect(screen.getByText("1 exchange left")).toBeInTheDocument();
  });
});

describe("SceneTermsCard", () => {
  it("names the other ruler and the end turn, and reports the player's choice", () => {
    const onConfirm = vi.fn();
    const onDecline = vi.fn();
    render(
      <SceneTermsCard
        card={CARD}
        counterpartName="Mira of Ashford"
        currentTurn={4}
        isBusy={false}
        onConfirm={onConfirm}
        onDecline={onDecline}
      />,
    );
    expect(
      screen.getByText(
        "A non-aggression pact with Mira of Ashford for 8 turns, ending on turn 12.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Nothing is binding until you sign.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign the pact" }));
    fireEvent.click(screen.getByRole("button", { name: "Decline" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onDecline).toHaveBeenCalledTimes(1);
  });
});

describe("SceneOutcomeBanner", () => {
  it.each([
    ["agreed", "The pact is sealed."],
    ["walked_out", "The ruler walked out of the talks."],
    ["refused", "The pact was refused."],
  ] as const)("announces a %s result", (result, text) => {
    render(
      <SceneOutcomeBanner outcome={{ kind: "terms_card", result }} onClose={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(text);
  });

  it("closes the scene on request", () => {
    const onClose = vi.fn();
    render(<SceneOutcomeBanner outcome={null} onClose={onClose} />);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("SceneTranscript", () => {
  it("shows past exchanges, then the pending message with the streaming reply", () => {
    render(
      <SceneTranscript
        exchanges={[{ sequence: 1, player_text: "Peace?", leader_text: "Perhaps." }]}
        leaderName="Mira"
        pendingPlayerText="Ten turns?"
        streamingReply="Eight, at least"
      />,
    );
    expect(screen.getByText("Peace?")).toBeInTheDocument();
    expect(screen.getByText("Perhaps.")).toBeInTheDocument();
    expect(screen.getByText("Ten turns?")).toBeInTheDocument();
    expect(screen.getByText("Eight, at least")).toBeInTheDocument();
  });

  it("shows an ellipsis until the first chunk arrives", () => {
    render(
      <SceneTranscript
        exchanges={[]}
        leaderName="Mira"
        pendingPlayerText="Hello"
        streamingReply=""
      />,
    );
    expect(screen.getByText("…")).toBeInTheDocument();
  });
});
