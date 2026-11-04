import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EngagementChronicle } from "../EngagementChronicle";

const prediction = {
  title: "Next exchange",
  friendlyLosses: "−140 (100–180)",
  enemyLosses: "−480 (400–560)",
  note: "Their troop mix is unscouted, so an even mix is assumed.",
};

const report = (exchange: number, minimum: number, maximum: number) => ({
  battle_id: "b1",
  campaign_turn: 1,
  exchange_index: exchange,
  total_exchange: exchange,
  own_losses: { infantry: 40, archers_siege: 5 },
  opponent_strength: { minimum, maximum },
  outcome: null,
});

describe("EngagementChronicle", () => {
  it("reports our fallen by troop type and how the enemy estimate narrowed", () => {
    render(
      <EngagementChronicle
        reports={[report(1, 900, 1300), report(2, 950, 1100)]}
        activeDoctrineName="hold"
        prediction={prediction}
      />,
    );

    expect(screen.getAllByText(/Our fallen: Infantry 40, Archers & siege 5/)).toHaveLength(2);
    expect(screen.getByText(/estimated at 950–1,100 \(was 900–1,300\)/)).toBeInTheDocument();
  });
});

describe("EngagementChronicle prediction", () => {
  it("shows the engine's expected losses with their range and no placeholder labels", () => {
    render(<EngagementChronicle reports={[]} activeDoctrineName="hold" prediction={prediction} />);

    expect(screen.getByText("−140 (100–180)")).toBeInTheDocument();
    expect(screen.getByText("−480 (400–560)")).toBeInTheDocument();
    expect(screen.getByText(/even mix is assumed/)).toBeInTheDocument();
    expect(screen.queryByText(/illustrative/i)).not.toBeInTheDocument();
  });

  it("shows no prediction card when the engine gave none", () => {
    render(<EngagementChronicle reports={[]} activeDoctrineName="hold" prediction={null} />);

    expect(screen.queryByText("Next exchange")).not.toBeInTheDocument();
  });
});
