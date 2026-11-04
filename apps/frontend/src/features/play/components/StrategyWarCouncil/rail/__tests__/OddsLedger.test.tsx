import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OddsLedger } from "../OddsLedger";
import type { TacticalOddsEstimate } from "../../StrategyWarCouncil.types";

const mockOdds: TacticalOddsEstimate = {
  balancePercent: 58,
  tierText: "Favorable",
  confidence: "medium",
  basis: "assumed_even_mix",
  factors: [
    {
      id: "weather",
      name: "Weather",
      icon: "cloud",
      valuePercent: 10,
      isPositive: true,
      title: "Weather modifier",
      explanation: "How today's weather scales attack pressure for your troops.",
    },
  ],
  playerLoss: { low: 90, expected: 140, high: 190 },
  enemyLoss: { low: 400, expected: 480, high: 560 },
};

describe("OddsLedger", () => {
  it("renders tactical balance meter and factor items with hover popover", () => {
    render(
      <OddsLedger
        odds={mockOdds}
        playerFactionName="Valenreach"
        enemyFactionName="Ironmark"
      />,
    );

    expect(screen.getByText("58% Favorable")).toBeInTheDocument();
    expect(screen.getByText("Valenreach (58%)")).toBeInTheDocument();
    expect(screen.getByText("Ironmark (42%)")).toBeInTheDocument();
    expect(screen.getByText("Weather")).toBeInTheDocument();
  });
});
