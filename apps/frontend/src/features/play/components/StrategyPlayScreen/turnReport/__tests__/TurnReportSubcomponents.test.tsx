import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuickStatsTicker } from "../QuickStatsTicker";
import { BattleReportCard } from "../BattleReportCard";
import { EconomyLedgerCard } from "../EconomyLedgerCard";
import { ReportItemCard } from "../ReportItemCard";
import type {
  BattleReportItem,
  EconomyLedgerLine,
  ReportItem,
} from "../../../../types/turnReport.types";

describe("Turn Report Subcomponents", () => {
  it("renders QuickStatsTicker with signed deltas", () => {
    render(
      <QuickStatsTicker
        stats={{
          netGold: -22,
          totalCasualties: 184,
          stability: 78,
          stabilityDelta: -4,
          manpower: 3240,
        }}
      />,
    );
    expect(screen.getByText("-22g")).toBeInTheDocument();
    expect(screen.getByText("184")).toBeInTheDocument();
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("(-4%)")).toBeInTheDocument();
    expect(screen.getByText("3,240")).toBeInTheDocument();
  });

  it("renders QuickStatsTicker with positive deltas", () => {
    render(
      <QuickStatsTicker
        stats={{
          netGold: 15,
          totalCasualties: 0,
          stability: 85,
          stabilityDelta: 2,
          manpower: 4000,
        }}
      />,
    );
    expect(screen.getByText("+15g")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("(+2%)")).toBeInTheDocument();
  });

  it("renders BattleReportCard and expands tactical rounds on toggle", () => {
    const battle: BattleReportItem = {
      id: "b1",
      name: "Battle of Greywater Ford",
      regionId: "greywater_ford",
      regionName: "Greywater Ford",
      outcome: "decisive_victory",
      summary: "Lord Raymond outflanked Hollin forces.",
      rounds: [
        {
          round: 1,
          description: "Archers exchange fire",
          varnCasualties: 32,
          rivalCasualties: 64,
        },
        {
          round: 2,
          description: "Cavalry envelopment",
          outcomeNote: "Hollin Routed",
        },
      ],
      varnLosses: 184,
      rivalLosses: 412,
      warScoreDelta: 14,
    };
    const onFocusMap = vi.fn();

    render(<BattleReportCard battle={battle} onFocusMap={onFocusMap} />);
    expect(screen.getByText("Battle of Greywater Ford")).toBeInTheDocument();
    expect(screen.getByText("Decisive Victory")).toBeInTheDocument();

    const mapBtn = screen.getByRole("button", { name: /map/i });
    fireEvent.click(mapBtn);
    expect(onFocusMap).toHaveBeenCalledWith("greywater_ford");

    // Toggle expansion
    const toggleBtn = screen.getByRole("button", { name: /skirmish phases/i });
    fireEvent.click(toggleBtn);
    expect(screen.getByText(/Archers exchange fire/i)).toBeInTheDocument();
    expect(screen.getByText(/Cavalry envelopment/i)).toBeInTheDocument();

    // Toggle collapse
    fireEvent.click(toggleBtn);
    expect(screen.queryByText(/Archers exchange fire/i)).not.toBeInTheDocument();
  });

  it("renders EconomyLedgerCard with calculation breakdown", () => {
    const lines: EconomyLedgerLine[] = [
      { label: "Tax Income", amount: 112, category: "tax" },
      { label: "Army Upkeep", amount: -96, category: "upkeep" },
    ];
    render(<EconomyLedgerCard lines={lines} netGold={16} />);
    expect(screen.getByText("Tax Income")).toBeInTheDocument();
    expect(screen.getByText("+112g")).toBeInTheDocument();
    expect(screen.getByText("-96g")).toBeInTheDocument();
    expect(screen.getByText("+16g")).toBeInTheDocument();
  });

  it("renders ReportItemCard with badge and action", () => {
    const item: ReportItem = {
      id: "item1",
      category: "internal",
      title: "Ashford Unrest",
      description: "Murmurs spread among merchants.",
      badge: { label: "Restless", tone: "warning" },
      signedValue: "-4%",
      regionId: "ashford",
    };
    const onFocusMap = vi.fn();
    render(<ReportItemCard item={item} onFocusMap={onFocusMap} />);
    expect(screen.getByText("Ashford Unrest")).toBeInTheDocument();
    expect(screen.getByText("Restless")).toBeInTheDocument();
    expect(screen.getByText("-4%")).toBeInTheDocument();

    const mapBtn = screen.getByRole("button", { name: /map/i });
    fireEvent.click(mapBtn);
    expect(onFocusMap).toHaveBeenCalledWith("ashford");
  });
});
