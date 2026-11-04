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

vi.mock("../../../hooks/useRestoredTurnReport", () => ({
  useRestoredTurnReport: () => undefined,
}));
vi.mock("../../../hooks/useResumePendingBattleSpeech", () => ({
  useResumePendingBattleSpeech: () => undefined,
}));
vi.mock("../../../hooks/useHistoricalWorld", () => ({
  useHistoricalWorld: () => ({ data: undefined, isFetching: false, isError: false }),
}));
vi.mock("../../../hooks/usePendingEventNarratives", () => ({
  usePendingEventNarratives: vi.fn(),
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

vi.mock("../../../hooks/useLiveLetter", () => ({
  useLiveLetter: () => ({
    pkg: null,
    isOpen: false,
    isLetterScene: false,
    isSceneTypeResolved: true,
    dispatchNumber: undefined,
    failureMessage: null,
    handleOpen: vi.fn(),
    handleClose: vi.fn(),
    handleSeal: vi.fn(),
    handleDecline: vi.fn(),
    requestScribeDraft: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useLiveJudgment", () => ({
  useLiveJudgment: () => ({
    pkg: null,
    isOpen: false,
    isJudgmentScene: false,
    isSceneTypeResolved: true,
    isStreaming: false,
    liveText: "",
    failureMessage: null,
    handleSpeak: vi.fn(),
    handlePronounce: vi.fn(),
    handleDismissReveal: vi.fn(),
    handleClose: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useStrategyDiplomacy", () => ({
  useStrategyDiplomacy: () => ({
    diplomacy: { pacts: [], isProposalAvailable: false, onProposeTerms: vi.fn() },
    sceneId: null,
    errorMessage: null,
  }),
}));

const mockUseStrategyMap = vi.fn(() => ({
  data: null as null | {
    schema_version: number;
    source: "manual";
    width: number;
    height: number;
    image_url: string | null;
    regions: {
      id: string;
      name: string;
      terrain: "plain" | "mountain";
      outline: string;
      label_point: { x: number; y: number };
      neighbor_ids: string[];
      source_color: string | null;
      source_ref: string | null;
    }[];
    roads: never[];
  },
  isLoading: false,
  isError: false,
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => mockUseStrategyMap(),
}));

describe("StrategyPlayScreen Integration", () => {
  beforeEach(() => {
    mockEndTurn.mockClear();
    mockUseStrategyMap.mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
    });
    useStrategyPlayStore.getState().reset();
  });

  it("renders full HUD, End Turn button, and empty map state when scenario has no custom map", () => {
    render(<StrategyPlayScreen />);
    expect(screen.getByText("King Alden IV")).toBeInTheDocument();
    expect(screen.getByText("End Turn")).toBeInTheDocument();
    expect(screen.getByText("No realm cartography available")).toBeInTheDocument();
    expect(screen.queryByText("Dunmere Vale")).not.toBeInTheDocument();
  });

  it("installs no window hook for triggering a letter", () => {
    render(<StrategyPlayScreen />);
    expect((window as unknown as Record<string, unknown>).__TRIGGER_LETTER__).toBeUndefined();
  });

  it("renders map skeleton while map data is loading", () => {
    mockUseStrategyMap.mockReturnValue({
      data: null,
      isLoading: true,
      isError: false,
    });

    render(<StrategyPlayScreen />);
    expect(screen.getByRole("status", { name: /loading map/i })).toBeInTheDocument();
    expect(screen.getByText("Unfurling realm cartography...")).toBeInTheDocument();
    expect(screen.queryByText("Dunmere Vale")).not.toBeInTheDocument();
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

  it("closes the report drawer and does not end turn when clicking Continue", () => {
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
    expect(useStrategyPlayStore.getState().isTurnReportOpen).toBe(false);
    expect(mockEndTurn).not.toHaveBeenCalled();
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
