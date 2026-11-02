import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrategyPlayScreen } from "../StrategyPlayScreen";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import { DEFAULT_PREVIEW_WORLD } from "../../StrategyPlayScreen/defaultPreviewWorld";
import * as simulationApi from "../../../api/simulation.api";
import type { StrategyTurnReportData } from "../../../types/turnReport.types";

vi.mock("../../../api/simulation.api");
vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: vi.fn(() => ({ data: undefined, isLoading: false })),
}));

const mockReport: StrategyTurnReportData = {
  turn: 1,
  seasonTitle: "Autumn, Year 1042",
  headline: "Seasonal Ledger & Realm Dispatches",
  quickStats: {
    netGold: 0,
    totalCasualties: 0,
    stability: 60,
    stabilityDelta: 0,
    manpower: 14200,
  },
  battles: [],
  economyLines: [
    { label: "Provincial Taxes", amount: 84, category: "tax" },
    { label: "Military Upkeep", amount: -40, category: "upkeep" },
  ],
  items: [],
  estimatedSections: ["economy_lines", "stability_delta", "manpower_delta"],
};

function renderStrategyScreen() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  queryClient.setQueryData(["simulation-world", "test-pt"], DEFAULT_PREVIEW_WORLD);

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <StrategyPlayScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Strategy Loop Stability and Layout Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStrategyPlayStore.getState().reset();
  });

  it("surfaces estimated banner and [Estimated] tags when report data is estimated", () => {
    useStrategyPlayStore.getState().setLatestReport(mockReport);
    useStrategyPlayStore.getState().openTurnReport();

    renderStrategyScreen();

    // Verify drawer opened
    expect(screen.getByRole("heading", { name: /seasonal ledger & realm dispatches/i })).toBeInTheDocument();

    // Verify estimated disclaimer banner
    expect(
      screen.getByText(/dispatches delayed — seasonal ledger estimated from realm records/i),
    ).toBeInTheDocument();

    // Verify [Estimated] tags on metrics and card
    expect(screen.getAllByText(/\[Estimated\]/i)).toHaveLength(2);
    expect(screen.getByText(/\(Estimated\)/i)).toBeInTheDocument();
  });

  it("closes the turn report drawer on Continue click without triggering turn resolution", async () => {
    useStrategyPlayStore.getState().setLatestReport(mockReport);
    useStrategyPlayStore.getState().openTurnReport();

    renderStrategyScreen();

    const continueButton = screen.getByRole("button", { name: /continue to next turn/i });
    fireEvent.click(continueButton);

    await waitFor(() => {
      expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
    });

    expect(simulationApi.endTurn).not.toHaveBeenCalled();
  });
});
