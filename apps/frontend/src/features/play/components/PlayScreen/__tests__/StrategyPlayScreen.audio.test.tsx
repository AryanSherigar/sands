import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrategyPlayScreen } from "../StrategyPlayScreen";
import { usePlayStore } from "../../../stores/play.store";
import { useStrategyPlayStore } from "../../../stores/strategyPlay.store";
import { LetterAmbientCanopy } from "../../StrategyPlayScreen/letter/LetterAmbientCanopy";

const mockUseStrategyAudio = vi.fn();
vi.mock("../../../hooks/useStrategyAudio", () => ({
  useStrategyAudio: (args: unknown) => mockUseStrategyAudio(args),
}));

function renderScreen() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <StrategyPlayScreen />
    </QueryClientProvider>,
  );
}

const mockWorld: { current: unknown } = {
  current: {
    world_version: 1,
    turn: 1,
    wave: 0,
    status: "planning",
    battles: [],
    clock: { turn: 1, start_year: 1042, start_month: 7 },
    my_faction: {
      id: "f1",
      name: "Kingdom of High Cairn",
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
};

const mockLetter: { current: Record<string, unknown> } = {
  current: {
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
  },
};

const mockNegotiation: { current: Record<string, unknown> } = {
  current: {
    diplomacy: { pacts: [], isProposalAvailable: false, onProposeTerms: vi.fn() },
    sceneId: null,
    errorMessage: null,
  },
};

const mockEvent: { current: Record<string, unknown> } = {
  current: {
    eventPackage: null,
    isResolving: false,
    resolveChoice: vi.fn(),
  },
};

vi.mock("react-router-dom", () => ({
  useParams: () => ({ id: "test-playthrough-123" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../../../hooks/useSimulationWorld", () => ({
  useSimulationWorld: () => ({
    data: mockWorld.current,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
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

vi.mock("../../../hooks/useLiveLetter", () => ({
  useLiveLetter: () => mockLetter.current,
}));

vi.mock("../../../hooks/useStrategyDiplomacy", () => ({
  useStrategyDiplomacy: () => mockNegotiation.current,
}));

vi.mock("../../../hooks/useStrategyEvent", () => ({
  useStrategyEvent: () => mockEvent.current,
}));

vi.mock("../../../hooks/useStrategyMap", () => ({
  useStrategyMap: () => ({
    data: null,
    isLoading: false,
    isError: false,
  }),
}));

describe("StrategyPlayScreen Audio Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useStrategyPlayStore.getState().reset();
    usePlayStore.setState({
      is_audio_muted: false,
      audio_volume: 0.8,
    });
    mockWorld.current = {
      world_version: 1,
      turn: 1,
      wave: 0,
      status: "planning",
      battles: [],
      clock: { turn: 1, start_year: 1042, start_month: 7 },
      my_faction: {
        id: "f1",
        name: "Kingdom of High Cairn",
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
    };
    mockLetter.current = {
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
    };
    mockNegotiation.current = {
      diplomacy: { pacts: [], isProposalAvailable: false, onProposeTerms: vi.fn() },
      sceneId: null,
      errorMessage: null,
    };
    mockEvent.current = {
      eventPackage: null,
      isResolving: false,
      resolveChoice: vi.fn(),
    };
  });

  it("mounts useStrategyAudio and passes activeWorld, playthroughId, and map context by default", () => {
    renderScreen();

    expect(mockUseStrategyAudio).toHaveBeenCalledWith(
      expect.objectContaining({
        worldState: mockWorld.current,
        uiContext: "map",
        seed: "test-playthrough-123",
      }),
    );
  });

  it("resolves activeContext to 'letter' when letter modal is open", () => {
    mockLetter.current = {
      ...mockLetter.current,
      pkg: {
        sceneId: "scene-letter-1",
        dispatchId: "dispatch-12",
        dispatchNumber: 12,
        provenance: {
          portraitUrl: "/portraits/vane.png",
          senderName: "Lady Vane",
          senderTitle: "Castellan",
          factionName: "Vane",
          crestUrl: "/crests/vane.png",
        },
        incoming: {
          senderName: "Lady Vane",
          senderTitle: "Castellan",
          factionName: "Vane",
          dateSolar: "Harvestide",
          subject: "Border skirmish",
          salutation: "Greetings",
          locationHeader: "High Cairn",
          isSealIntactPriorToDawn: true,
          paragraphs: ["My Lord..."],
          signoffPlace: "High Cairn",
          signoffSignature: "Lady Vane",
        },
        scribe: { name: "Aldous", opinion: 60, advice: "Sign it" },
        initialDraft: {
          revisionIndex: 0,
          instruction: "Initial",
          salutation: "Greetings",
          paragraphs: ["Draft"],
          signoffText: "Faithfully",
          authorTitle: "King",
        },
      },
      isOpen: true,
    };

    renderScreen();

    expect(mockUseStrategyAudio).toHaveBeenCalledWith(
      expect.objectContaining({
        uiContext: "letter",
      }),
    );
  });

  it("resolves activeContext to 'negotiation' when diplomacy scene is active", () => {
    mockNegotiation.current = {
      ...mockNegotiation.current,
      sceneId: "scene-diplo-1",
    };
    mockLetter.current = {
      ...mockLetter.current,
      isSceneTypeResolved: true,
      isLetterScene: false,
    };

    renderScreen();

    expect(mockUseStrategyAudio).toHaveBeenCalledWith(
      expect.objectContaining({
        uiContext: "negotiation",
      }),
    );
  });

  it("resolves activeContext to 'event' when eventPackage is present", () => {
    mockEvent.current = {
      ...mockEvent.current,
      eventPackage: {
        sceneId: "event-1",
        category: "trouble",
        title: "Drought",
        subheading: "Harvest crisis",
        turnText: "Turn 1",
        bodyProse: "Drought strikes...",
        character: {
          name: "Lord Harl",
          title: "Castellan",
          disposition: "Resentful",
          avatarUrl: "/avatars/harl.png",
        },
        choices: [],
      },
    };

    renderScreen();

    expect(mockUseStrategyAudio).toHaveBeenCalledWith(
      expect.objectContaining({
        uiContext: "event",
      }),
    );
  });

  it("resolves activeContext to 'war_council' when activeWorld status is awaiting_battle_decision", () => {
    mockWorld.current = {
      ...(mockWorld.current as Record<string, unknown>),
      status: "awaiting_battle_decision",
    };

    renderScreen();

    expect(mockUseStrategyAudio).toHaveBeenCalledWith(
      expect.objectContaining({
        uiContext: "war_council",
      }),
    );
  });

  it("resolves activeContext to 'turn_report' when turn report is open", () => {
    useStrategyPlayStore.setState({ isTurnReportOpen: true });

    renderScreen();

    expect(mockUseStrategyAudio).toHaveBeenCalledWith(
      expect.objectContaining({
        uiContext: "turn_report",
      }),
    );
  });

  it("toggles is_audio_muted in usePlayStore when clicking ambient audio toggle in canopy", () => {
    renderScreen();

    const muteBtn = screen.getByRole("button", {
      name: /toggle ambient strategy audio/i,
    });
    expect(muteBtn).toBeInTheDocument();
    expect(usePlayStore.getState().is_audio_muted).toBe(false);

    fireEvent.click(muteBtn);
    expect(usePlayStore.getState().is_audio_muted).toBe(true);

    fireEvent.click(muteBtn);
    expect(usePlayStore.getState().is_audio_muted).toBe(false);
  });

  it("LetterAmbientCanopy triggers setIsAudioMuted in usePlayStore and calls onToggleMute", () => {
    const onToggleMuteMock = vi.fn();
    render(
      <LetterAmbientCanopy
        stage="reading"
        dispatchNumber={1}
        dateSolar="Autumn 1042"
        isMuted={false}
        onReturnToDesk={vi.fn()}
        onToggleMute={onToggleMuteMock}
      />,
    );

    const studyAudioBtn = screen.getByRole("button", {
      name: /toggle ambient study audio/i,
    });
    expect(studyAudioBtn).toBeInTheDocument();
    expect(usePlayStore.getState().is_audio_muted).toBe(false);

    fireEvent.click(studyAudioBtn);
    expect(onToggleMuteMock).toHaveBeenCalledTimes(1);
    expect(usePlayStore.getState().is_audio_muted).toBe(true);
  });
});
