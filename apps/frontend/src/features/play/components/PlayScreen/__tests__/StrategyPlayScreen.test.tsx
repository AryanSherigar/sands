import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StrategyPlayScreen } from "../StrategyPlayScreen";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";

const mockEndTurn = vi.fn();

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-playthrough" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../../../hooks/useSimulationWorld", () => ({
  useSimulationWorld: () => ({
    data: {
      world_version: 1,
      turn: 1,
      wave: 0,
      status: "planning",
      battles: [],
      clock: { turn: 1, start_year: 1042, start_month: 7 },
      my_faction: {
        id: "f1",
        treasury: 340,
        manpower: 14200,
        stability: 2,
        war_exhaustion: 0,
        reputation: 50,
        tax_rate: "normal",
        loans: [],
      },
      ruler: { name: "King Alden IV" },
      regions: [],
      armies: [],
      rivals: [],
      queued_orders: [],
      orders_remaining: 4,
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useEndTurn", () => ({
  useEndTurn: () => ({
    endTurn: mockEndTurn,
    isEndingTurn: false,
    lastTurnResult: null,
    errorInfo: null,
  }),
}));

vi.mock("../../../hooks/useSimulationCommands", () => ({
  useSimulationCommands: () => ({
    acceptMutation: { mutate: vi.fn(), isPending: false },
    cancelMutation: { mutate: vi.fn(), isPending: false },
    check: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useStrategyEvent", () => ({
  useStrategyEvent: () => ({
    eventPackage: null,
    isResolving: false,
    resolveChoice: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useStrategyDiplomacy", () => ({
  useStrategyDiplomacy: () => ({
    diplomacy: { pacts: [], isProposalAvailable: false, onProposeTerms: vi.fn() },
    sceneId: null,
    errorMessage: null,
  }),
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({
    data: null,
    isLoading: false,
    isError: false,
  }),
}));

describe("StrategyPlayScreen Integration", () => {
  beforeEach(() => {
    mockEndTurn.mockClear();
    useStrategyPlayStore.getState().reset();
  });

  it("renders full HUD and End Turn button", () => {
    render(<StrategyPlayScreen />);
    expect(screen.getByText("King Alden IV")).toBeInTheDocument();
    expect(screen.getByText("End Turn")).toBeInTheDocument();
    expect(screen.getByText("Dunmere Vale")).toBeInTheDocument();
  });

  it("mounts turn report launcher button", () => {
    render(<StrategyPlayScreen />);
    expect(screen.getByRole("button", { name: /turn report/i })).toBeInTheDocument();
  });

  it("mounts turn report launcher and toggles the drawer on click", () => {
    useStrategyPlayStore.getState().setLatestReport({
      turn: 2,
      seasonTitle: "Summer, Year 3",
      headline: "Peace reigns across the realm",
      quickStats: {
        netGold: 10,
        totalCasualties: 0,
        stability: 80,
        stabilityDelta: 1,
        manpower: 5000,
      },
      battles: [],
      economyLines: [],
      items: [],
    });

    render(<StrategyPlayScreen />);
    const launcher = screen.getByRole("button", { name: /turn report/i });
    expect(launcher).toBeInTheDocument();

    expect(screen.queryByText("Peace reigns across the realm")).not.toBeInTheDocument();

    fireEvent.click(launcher);
    expect(screen.getByText("Peace reigns across the realm")).toBeInTheDocument();

    fireEvent.click(launcher);
    expect(screen.queryByText("Peace reigns across the realm")).not.toBeInTheDocument();
  });

  it("calls endTurn when ending turn through End Turn module", () => {
    render(<StrategyPlayScreen />);
    const endTurnBtn = screen.getByRole("button", { name: /end turn/i });
    fireEvent.click(endTurnBtn);
    const confirmBtn = screen.getByRole("button", { name: /^end turn$/i });
    fireEvent.click(confirmBtn);
    expect(mockEndTurn).toHaveBeenCalled();
  });

  it("calls endTurn when clicking Continue in StrategyTurnReportDrawer", () => {
    useStrategyPlayStore.getState().setLatestReport({
      turn: 2,
      seasonTitle: "Summer, Year 3",
      headline: "Peace reigns across the realm",
      quickStats: {
        netGold: 10,
        totalCasualties: 0,
        stability: 80,
        stabilityDelta: 1,
        manpower: 5000,
      },
      battles: [],
      economyLines: [],
      items: [],
    });
    useStrategyPlayStore.getState().openTurnReport();

    render(<StrategyPlayScreen />);
    const continueBtn = screen.getByRole("button", { name: /continue to next turn/i });
    fireEvent.click(continueBtn);
    expect(mockEndTurn).toHaveBeenCalled();
  });

  it("toggles the situations drawer when clicking active crises in top canopy", () => {
    useStrategyPlayStore.getState().openSituations();
    render(<StrategyPlayScreen />);
    expect(screen.getByRole("heading", { name: /^situations$/i })).toBeDefined();

    const closeBtn = screen.getByRole("button", { name: /^close$/i });
    fireEvent.click(closeBtn);
    expect(useStrategyPlayStore.getState().isSituationsOpen).toBe(false);
  });
});
