import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OddsLedger } from "../OddsLedger";
import type { TacticalOddsEstimate } from "../../StrategyWarCouncil.types";

const mockOdds: TacticalOddsEstimate = {
  balancePercent: 58,
  isRange: false,
  minPercent: 58,
  maxPercent: 58,
  tierText: "Decisive",
  factors: [
    {
      id: "terrain",
      name: "Terrain: Sloped Ford",
      icon: "landscape",
      valuePercent: 10,
      isPositive: true,
      title: "Sloped Ford Mechanics",
      explanation: "Holding defensive slope: +10% Net.",
    },
  ],
  playerLossEstimated: 140,
  enemyLossEstimated: 480,
  warScoreEstimated: 28,
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

    expect(screen.getByText("+58% Decisive")).toBeInTheDocument();
    expect(screen.getByText("Valenreach (58%)")).toBeInTheDocument();
    expect(screen.getByText("Ironmark (42%)")).toBeInTheDocument();
    expect(screen.getByText("Terrain: Sloped Ford")).toBeInTheDocument();
  });
});
