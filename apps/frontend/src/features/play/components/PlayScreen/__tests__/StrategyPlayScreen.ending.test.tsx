import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import { StrategyPlayScreen } from "../StrategyPlayScreen";

const state = vi.hoisted(() => ({
  ending: null as null | Record<string, unknown>,
  navigate: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-playthrough" }),
  useNavigate: () => state.navigate,
}));

vi.mock("../../../hooks/useSimulationWorld", () => ({
  useSimulationWorld: () => ({
    data: {
      world_version: 1,
      turn: 5,
      wave: 0,
      status: "planning",
      ending: state.ending,
      scene_id: null,
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

vi.mock("../../../hooks/usePendingEventNarratives", () => ({
  usePendingEventNarratives: () => undefined,
}));
vi.mock("../../../hooks/useResumePendingBattleSpeech", () => ({
  useResumePendingBattleSpeech: () => undefined,
}));
vi.mock("../../../hooks/useHistoricalWorld", () => ({
  useHistoricalWorld: () => ({ data: undefined, isFetching: false, isError: false }),
}));
vi.mock("../../../hooks/useRestoredTurnReport", () => ({
  useRestoredTurnReport: () => undefined,
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

vi.mock("../../StrategyChronicleBook/StrategyChronicleBook", () => ({
  StrategyChronicleBook: ({ rulerName, onClose }: { rulerName: string; onClose: () => void }) => (
    <div data-testid="chronicle-book">
      {rulerName}
      <button type="button" onClick={onClose}>Close the book</button>
    </div>
  ),
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({ data: null, isLoading: false, isError: false }),
}));

vi.mock("../../StrategyPlayScreen/scene/StrategySceneDialog", () => ({
  StrategySceneDialog: () => <div data-testid="generic-scene-dialog" />,
}));


describe("StrategyPlayScreen ending", () => {
  beforeEach(() => {
    state.ending = null;
    state.navigate.mockReset();
    useStrategyPlayStore.getState().reset();
  });

  it("keeps End Turn available and shows no overlay while the reign continues", () => {
    render(<StrategyPlayScreen />);
    expect(screen.getByText("End Turn").closest("button")).not.toBeDisabled();
    expect(screen.queryByRole("dialog", { name: /reign has ended/i })).toBeNull();
  });

  it("shows the tier and locks End Turn once the world has an ending", () => {
    state.ending = { ending_id: "default_defeat_capital_lost", kind: "defeat", turn: 5 };
    render(<StrategyPlayScreen />);
    expect(screen.getByRole("dialog", { name: /reign has ended/i })).toBeInTheDocument();
    expect(screen.getByText("Ruin")).toBeInTheDocument();
    expect(screen.getByText("End Turn").closest("button")).toBeDisabled();
  });

  it("sends the player back to the scenario page", () => {
    state.ending = { ending_id: "default_graded_end_date", kind: "graded", turn: 29, grade: "honorable" };
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getByRole("button", { name: "Return to the scenario page" }));
    expect(state.navigate).toHaveBeenCalledWith("/discover");
  });

  it("opens the chronicle book from Read the legacy and returns to the ending screen on close", () => {
    state.ending = { ending_id: "default_graded_end_date", kind: "graded", turn: 29, grade: "honorable" };
    render(<StrategyPlayScreen />);
    fireEvent.click(screen.getByRole("button", { name: "Read the legacy" }));
    expect(screen.getByTestId("chronicle-book")).toHaveTextContent("King Alden IV");
    expect(screen.queryByRole("dialog", { name: /reign has ended/i })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Close the book" }));
    expect(screen.queryByTestId("chronicle-book")).toBeNull();
    expect(screen.getByRole("dialog", { name: /reign has ended/i })).toBeInTheDocument();
  });
});
