import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { QuickStatsTicker } from "../QuickStatsTicker";
import type { TurnReportQuickStats } from "../../../../types/turnReport.types";

const BASE_STATS: TurnReportQuickStats = {
  netGold: 15,
  totalCasualties: 120,
  stability: 80,
  stabilityDelta: -3,
  manpower: 4500,
};

describe("QuickStatsTicker", () => {
  it("renders base stats without estimated notices when estimatedSections is empty", () => {
    render(<QuickStatsTicker stats={BASE_STATS} estimatedSections={[]} />);

    expect(screen.getByText("+15g")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("(-3%)")).toBeInTheDocument();
    expect(screen.getByText("4,500")).toBeInTheDocument();
    expect(screen.queryByText("[Estimated]")).not.toBeInTheDocument();
  });

  it("displays [Estimated] beside stability delta when stability_delta is in estimatedSections", () => {
    render(
      <QuickStatsTicker
        stats={BASE_STATS}
        estimatedSections={["stability_delta"]}
      />,
    );

    const estimatedBadges = screen.getAllByText("[Estimated]");
    expect(estimatedBadges).toHaveLength(1);
  });

  it("displays [Estimated] beside manpower when manpower_delta is in estimatedSections", () => {
    render(
      <QuickStatsTicker
        stats={BASE_STATS}
        estimatedSections={["manpower_delta"]}
      />,
    );

    const estimatedBadges = screen.getAllByText("[Estimated]");
    expect(estimatedBadges).toHaveLength(1);
  });

  it("displays [Estimated] beside both when both are estimated", () => {
    render(
      <QuickStatsTicker
        stats={BASE_STATS}
        estimatedSections={["stability_delta", "manpower_delta"]}
      />,
    );

    const estimatedBadges = screen.getAllByText("[Estimated]");
    expect(estimatedBadges).toHaveLength(2);
  });
});
