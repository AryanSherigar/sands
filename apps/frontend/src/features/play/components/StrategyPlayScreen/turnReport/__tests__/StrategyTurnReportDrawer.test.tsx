import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StrategyTurnReportDrawer } from "../StrategyTurnReportDrawer";
import { useStrategyPlayStore } from "../../../../stores/strategyPlay.store";
import type { StrategyTurnReportData } from "../../../../types/turnReport.types";

const TEST_REPORT: StrategyTurnReportData = {
  turn: 2,
  seasonTitle: "Summer, Year 3",
  headline: "Greywater Ford held; Ashford restless",
  quickStats: {
    netGold: -22,
    totalCasualties: 184,
    stability: 78,
    stabilityDelta: -4,
    manpower: 3240,
  },
  battles: [
    {
      id: "b1",
      name: "Battle of Greywater Ford",
      regionId: "greywater_ford",
      regionName: "Greywater Ford",
      outcome: "decisive_victory",
      summary: "River crossing secured.",
      rounds: [],
      varnLosses: 184,
      rivalLosses: 412,
      warScoreDelta: 14,
    },
  ],
  economyLines: [
    { label: "Tax income", amount: 112, category: "tax" },
  ],
  items: [
    {
      id: "d1",
      category: "internal",
      title: "Ashford Restless",
      description: "Tithe discontent.",
      regionId: "ashford",
    },
    {
      id: "d2",
      category: "diplomacy",
      title: "Saltmere Envoy",
      description: "Pact proposed.",
    },
  ],
};

describe("StrategyTurnReportDrawer", () => {
  beforeEach(() => {
    useStrategyPlayStore.getState().reset();
    useStrategyPlayStore.getState().setLatestReport(TEST_REPORT);
  });

  it("does not render when isTurnReportOpen is false", () => {
    const { container } = render(<StrategyTurnReportDrawer onContinue={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders seasonal header, turn chip, headline, quick stats, and cards when open", () => {
    useStrategyPlayStore.getState().openTurnReport();
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    expect(screen.getByText("Summer, Year 3")).toBeInTheDocument();
    expect(screen.getByText("Turn 2")).toBeInTheDocument();
    expect(screen.getByText("Greywater Ford held; Ashford restless")).toBeInTheDocument();
    expect(screen.getAllByText("-22g").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Battle of Greywater Ford")).toBeInTheDocument();
    expect(screen.getByText("Tax income")).toBeInTheDocument();
    expect(screen.getByText("Ashford Restless")).toBeInTheDocument();
    expect(screen.getByText("Saltmere Envoy")).toBeInTheDocument();
  });

  it("filters items when clicking category filter pills", () => {
    useStrategyPlayStore.getState().openTurnReport();
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    const diplomacyFilter = screen.getByRole("button", { name: /diplomacy/i });
    fireEvent.click(diplomacyFilter);

    expect(screen.getByText("Saltmere Envoy")).toBeInTheDocument();
    expect(screen.queryByText("Battle of Greywater Ford")).not.toBeInTheDocument();
    expect(screen.queryByText("Tax income")).not.toBeInTheDocument();

    const militaryFilter = screen.getByRole("button", { name: /military/i });
    fireEvent.click(militaryFilter);
    expect(screen.getByText("Battle of Greywater Ford")).toBeInTheDocument();
    expect(screen.queryByText("Saltmere Envoy")).not.toBeInTheDocument();

    const economyFilter = screen.getByRole("button", { name: /economy/i });
    fireEvent.click(economyFilter);
    expect(screen.getByText("Tax income")).toBeInTheDocument();
    expect(screen.queryByText("Battle of Greywater Ford")).not.toBeInTheDocument();

    const allFilter = screen.getByRole("button", { name: /all/i });
    fireEvent.click(allFilter);
    expect(screen.getByText("Battle of Greywater Ford")).toBeInTheDocument();
    expect(screen.getByText("Saltmere Envoy")).toBeInTheDocument();
  });

  it("toggles autoShowTurnReport with the checkbox", () => {
    useStrategyPlayStore.getState().openTurnReport();
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    const checkbox = screen.getByLabelText(/show report after each turn/i);
    expect(checkbox).toBeChecked();

    fireEvent.click(checkbox);
    expect(useStrategyPlayStore.getState().autoShowTurnReport).toBe(false);
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    expect(useStrategyPlayStore.getState().autoShowTurnReport).toBe(true);
    expect(checkbox).toBeChecked();
  });

  it("closes on Close / Dismiss button", () => {
    useStrategyPlayStore.getState().openTurnReport();
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    const closeBtn = screen.getByRole("button", { name: /close report/i });
    fireEvent.click(closeBtn);
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("closes on Escape key press", () => {
    useStrategyPlayStore.getState().openTurnReport();
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    fireEvent.keyDown(window, { key: "Escape" });
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("invokes onContinue and closes report on Continue button click", () => {
    useStrategyPlayStore.getState().openTurnReport();
    const handleContinue = vi.fn();
    render(<StrategyTurnReportDrawer onContinue={handleContinue} />);

    const continueBtn = screen.getByRole("button", { name: /continue to next turn/i });
    fireEvent.click(continueBtn);
    expect(handleContinue).toHaveBeenCalled();
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
  });

  it("renders empty state when no report is available", () => {
    useStrategyPlayStore.getState().setLatestReport(null);
    useStrategyPlayStore.getState().openTurnReport();
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    expect(screen.getByText(/no turn report available/i)).toBeInTheDocument();
  });

  it("renders empty state when no items match the selected filter", () => {
    useStrategyPlayStore.getState().openTurnReport();
    useStrategyPlayStore.getState().setLatestReport({
      ...TEST_REPORT,
      battles: [],
      economyLines: [],
      items: [],
    });
    render(<StrategyTurnReportDrawer onContinue={() => {}} />);

    expect(screen.getByText(/no events recorded/i)).toBeInTheDocument();
  });

  it("triggers focusMapLocation when map button is clicked on battle or report item", () => {
    useStrategyPlayStore.getState().openTurnReport();
    const handleFocusMap = vi.fn();
    render(<StrategyTurnReportDrawer onContinue={() => {}} onFocusMap={handleFocusMap} />);

    const mapButtons = screen.getAllByRole("button", { name: /map/i });
    fireEvent.click(mapButtons[0]);
    expect(handleFocusMap).toHaveBeenCalledWith("greywater_ford");
    expect(useStrategyPlayStore.getState().mapFocusTarget?.regionId).toBe("greywater_ford");
  });
});
