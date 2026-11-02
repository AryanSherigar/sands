import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NegotiationReadingChamber } from "../NegotiationReadingChamber";

describe("NegotiationReadingChamber", () => {
  it("renders situation dropcap, exchanges, and streaming response", () => {
    render(
      <NegotiationReadingChamber
        situation="The great hall of Valdren is cold."
        transcript={[
          {
            sequence: 1,
            player_text: "We come in peace.",
            leader_text: "Peace is costly in my lands.",
          },
        ]}
        leaderName="Queen Mira"
        pendingPlayerText="I offer mutual non-aggression."
        streamingReply="Let me consider that..."
        isStreaming={true}
      />
    );

    expect(screen.getByText(/The great hall of Valdren is cold/i)).toBeInTheDocument();
    expect(screen.getByText(/We come in peace/i)).toBeInTheDocument();
    expect(screen.getByText(/Peace is costly in my lands/i)).toBeInTheDocument();
    expect(screen.getByText(/I offer mutual non-aggression/i)).toBeInTheDocument();
    expect(screen.getByText(/Let me consider that/i)).toBeInTheDocument();
  });

  it("does not show a player card when the exchange has no player utterance", () => {
    render(
      <NegotiationReadingChamber
        situation=""
        transcript={[{ sequence: 1, player_text: "  ", leader_text: "We offer an end to this war." }]}
        leaderName="Queen Mira"
        isStreaming={false}
      />
    );

    expect(screen.queryByText("You spoke")).not.toBeInTheDocument();
    expect(screen.getByText(/We offer an end to this war/i)).toBeInTheDocument();
  });
});
