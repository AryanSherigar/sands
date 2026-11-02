import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { StrategyJudgmentPackage } from "../../../types/judgmentScene.types";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import { StrategyPlayScreen } from "../StrategyPlayScreen";

const state = vi.hoisted(() => ({
  worldStatus: "awaiting_scene",
  judgment: null as null | Record<string, unknown>,
  diplomacySceneId: null as string | null,
}));

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-playthrough" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../../../hooks/useSimulationWorld", () => ({
  useSimulationWorld: () => ({
    data: {
      world_version: 1,
      turn: 5,
      wave: 0,
      status: state.worldStatus,
      scene_id: "scene-j",
      battles: [],
      clock: { turn: 5, start_year: 1042, start_month: 7 },
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
vi.mock("../../../hooks/useHistoricalWorld", () => ({
  useHistoricalWorld: () => ({ data: undefined, isFetching: false, isError: false }),
}));
vi.mock("../../../hooks/usePendingEventNarratives", () => ({
  usePendingEventNarratives: vi.fn(),
}));
vi.mock("../../../hooks/useEndTurn", () => ({
  useEndTurn: () => ({
    endTurn: vi.fn(),
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
  useStrategyEvent: () => ({ eventPackage: null, isResolving: false, resolveChoice: vi.fn() }),
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
  useLiveJudgment: () => state.judgment,
}));

vi.mock("../../../hooks/useStrategyDiplomacy", () => ({
  useStrategyDiplomacy: () => ({
    diplomacy: { pacts: [], isProposalAvailable: false, onProposeTerms: vi.fn() },
    sceneId: state.diplomacySceneId,
    errorMessage: null,
  }),
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({ data: null, isLoading: false, isError: false }),
}));

vi.mock("../../StrategyPlayScreen/scene/StrategySceneDialog", () => ({
  StrategySceneDialog: () => <div data-testid="generic-scene-dialog" />,
}));

const judgmentPackage: StrategyJudgmentPackage = {
  sceneId: "scene-j",
  turn: 5,
  summary: "Harl stands accused.",
  charge: "treason",
  subjectKind: "governor",
  accused: { participantId: "harl", name: "Harl", kind: "governor", stance: null },
  advisors: [],
  openingText: "The hall is silent.",
  exchanges: [],
  spokenExchangesRemaining: 4,
  outcomeSummary: [],
  isResolved: false,
};

const judgmentHook = (overrides: Record<string, unknown> = {}) => ({
  pkg: judgmentPackage,
  isOpen: true,
  isJudgmentScene: true,
  isSceneTypeResolved: true,
  isStreaming: false,
  liveText: "",
  failureMessage: null,
  handleSpeak: vi.fn(() => Promise.resolve(true)),
  handlePronounce: vi.fn(() => Promise.resolve(true)),
  handleDismissReveal: vi.fn(),
  handleClose: vi.fn(),
  ...overrides,
});

describe("StrategyPlayScreen judgment scenes", () => {
  beforeEach(() => {
    state.worldStatus = "awaiting_scene";
    state.diplomacySceneId = null;
    state.judgment = judgmentHook();
    useStrategyPlayStore.getState().reset();
  });

  it("opens the judgment dialog when the world awaits a judgment scene", () => {
    render(<StrategyPlayScreen />);
    expect(screen.getByRole("dialog", { name: /judgment of harl/i })).toBeInTheDocument();
  });

  it("does not render the generic scene dialog for a judgment", () => {
    state.diplomacySceneId = "scene-j";
    render(<StrategyPlayScreen />);
    expect(screen.queryByTestId("generic-scene-dialog")).toBeNull();
  });

  it("still renders the generic scene dialog for other scenes", () => {
    state.diplomacySceneId = "scene-n";
    state.judgment = judgmentHook({ pkg: null, isOpen: false, isJudgmentScene: false });
    render(<StrategyPlayScreen />);
    expect(screen.getByTestId("generic-scene-dialog")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: /judgment/i })).toBeNull();
  });

  it("keeps End Turn disabled while a judgment is pending", () => {
    render(<StrategyPlayScreen />);
    expect(screen.getByText("End Turn").closest("button")).toBeDisabled();
  });
});
