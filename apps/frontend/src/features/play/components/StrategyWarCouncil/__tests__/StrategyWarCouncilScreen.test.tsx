import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type {
  WardConfig,
  WardIdentifier,
} from "../StrategyWarCouncil.types";
import { StrategyWarCouncilScreen } from "../StrategyWarCouncilScreen";

const mockWards: Record<WardIdentifier, WardConfig> = {
  left: {
    ward: "left",
    title: "Left Ward (Vanguard)",
    stance: "hold",
    isAnchor: false,
    ranks: [
      {
        id: "c-left-front",
        troopType: "infantry",
        name: "Vanguard Spearmen",
        count: 500,
        rankOrder: "front",
        tacticalRole: "Locks shields, braces against flank charges",
      },
      {
        id: "c-left-middle",
        troopType: "archers_siege",
        name: "Auxiliary Skirmishers",
        count: 200,
        rankOrder: "middle",
        tacticalRole: "Harasses approaching vanguard",
      },
      {
        id: "c-left-rear",
        troopType: "cavalry",
        name: "Outrider Horse",
        count: 100,
        rankOrder: "rear",
        tacticalRole: "Screens left flank",
      },
    ],
  },
  center: {
    ward: "center",
    title: "Center (Main Battle)",
    stance: "hold",
    isAnchor: true,
    ranks: [
      {
        id: "c-center-front",
        troopType: "infantry",
        name: "Shieldwall Spearmen",
        count: 600,
        rankOrder: "front",
        tacticalRole: "Locks shields and braces against shock charges",
      },
      {
        id: "c-center-middle",
        troopType: "archers_siege",
        name: "Longbowmen",
        count: 400,
        rankOrder: "middle",
        tacticalRole: "Volley fire into attacking center",
      },
      {
        id: "c-center-rear",
        troopType: "cavalry",
        name: "Armored Knights",
        count: 200,
        rankOrder: "rear",
        tacticalRole: "Shock reserve to exploit breaches",
      },
    ],
  },
  right: {
    ward: "right",
    title: "Right Ward (Rearguard)",
    stance: "hold",
    isAnchor: false,
    ranks: [
      {
        id: "c-right-front",
        troopType: "infantry",
        name: "Line Footmen",
        count: 400,
        rankOrder: "front",
        tacticalRole: "Anchors right slope and checks skirmishers",
      },
      {
        id: "c-right-middle",
        troopType: "archers_siege",
        name: "Crossbowmen",
        count: 150,
        rankOrder: "middle",
        tacticalRole: "Point-blank armor penetration",
      },
      {
        id: "c-right-rear",
        troopType: "cavalry",
        name: "Light Horse",
        count: 100,
        rankOrder: "rear",
        tacticalRole: "Watches the right perimeter",
      },
    ],
  },
};

let mockState: Record<string, unknown>;

vi.mock("../hooks/useWarCouncilState", () => ({
  useWarCouncilState: () => mockState,
}));

describe("StrategyWarCouncilScreen", () => {
  beforeEach(() => {
    mockState = {
      battle: {
        id: "battle-1",
        region_id: "ashford_ford",
        status: "awaiting_commands",
        outcome: null,
        current_turn: 1,
        exchanges_used: 0,
        total_exchanges: 4,
        is_big: true,
        control_mode: "player",
        terrain: "hills",
        weather: "rain",
        command_cost: 0,
        own_contingent: {
          faction_id: "valenreach",
          army_ids: ["army-1"],
          troops: { infantry: 1500, cavalry: 400, archers_siege: 750 },
          morale: 95,
          fatigue: 10,
          plan: {
            formation: "defensive",
            tactic: "hold",
            withdrawal_policy: "balanced",
            reserve_policy: "conserve",
          },
          supply: "supplied",
          status: "fighting",
        },
        opponents: [
          {
            faction_id: "ironmark",
            strength: { minimum: 1200, maximum: 1600 },
            reports: [],
          },
        ],
        legal_commands: ["set_plan", "reconnoitre", "withdraw", "surrender"],
      },
      reports: [],
      wards: mockWards,
      stagedPlan: {
        formation: "defensive",
        tactic: "hold",
        withdrawal_policy: "balanced",
        reserve_policy: "conserve",
      },
      activeAnchor: "center",
      reservePolicy: "conserve",
      canCommitReserves: true,
      canReconnoitre: true,
      canAddressTroops: false,
      speechReception: null,
      speechErrorMessage: null,
      isSpeaking: false,
      addressTroops: vi.fn().mockResolvedValue(true),
      setReservePolicy: vi.fn(),
      isCodexOpen: false,
      isRetreatModalOpen: false,
      odds: {
        balancePercent: 58,
        isRange: false,
        minPercent: 58,
        maxPercent: 58,
        tierText: "Decisive",
        factors: [],
        playerLossEstimated: 140,
        enemyLossEstimated: 480,
        warScoreEstimated: 28,
      },
      isCommitting: false,
      receiptReport: null,
      aftermath: null,
      isLoading: false,
      loadErrorMessage: null,
      retryLoad: vi.fn(),
      canCommitWave: true,
      canWithdraw: true,
      commandErrorMessage: null,
      isSendingCommand: false,
      closeReceipt: vi.fn(),
      updateCohortCount: vi.fn(),
      reorderRank: vi.fn(),
      setFormation: vi.fn(),
      setTactic: vi.fn(),
      setActiveDoctrine: vi.fn(),
      setAnchor: vi.fn(),
      commitWave: vi.fn().mockResolvedValue(undefined),
      commitBattle: vi.fn().mockResolvedValue(undefined),
      commitReserves: vi.fn().mockResolvedValue(undefined),
      soundWithdrawal: vi.fn().mockResolvedValue(undefined),
      toggleCodex: vi.fn(),
      toggleRetreatModal: vi.fn(),
      orderScoutMission: vi.fn().mockResolvedValue(undefined),
      confirmRetreat: vi.fn().mockResolvedValue(true),
    };
  });

  it("renders 3 columns with the real command cost and no invented frontage or commanders", () => {
    const handleReturn = vi.fn();
    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{ ashford_ford: "Ashford Ridge" }}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={handleReturn}
      />,
    );

    // HUD Header elements
    expect(screen.getByText("Battle of Ashford Ridge")).toBeInTheDocument();
    expect(screen.getByText("0 command points per order")).toBeInTheDocument();
    expect(screen.queryByText(/Frontage: 2,500/)).toBeNull();

    // Column 1: Left Rail (Tactical balance & commanders)
    expect(screen.getByText("Tactical Balance")).toBeInTheDocument();
    expect(screen.queryByText("Lord Aldric Vane")).toBeNull();

    // Column 2: Center Theater (Intel, Clash divider, PlayerWardRanks)
    expect(screen.getByText("Field of Battle")).toBeInTheDocument();
    expect(screen.getByText(/Our Battle Array \(Planning Sketch/)).toBeInTheDocument();
    expect(screen.getByText("Center (Main Battle)")).toBeInTheDocument();

    // Column 3: Right Pillar (Doctrines & Commit)
    expect(screen.getByText("Tactical Doctrines")).toBeInTheDocument();
    expect(screen.getByText("Commit to Battle")).toBeInTheDocument();

    // Back to map navigation
    const returnBtn = screen.getByText("Map of Ashford Ridge").closest("button");
    fireEvent.click(returnBtn!);
    expect(handleReturn).toHaveBeenCalled();
  });

  it("renders PlayerWardRanks with steppers and handles incrementing cohort count", () => {
    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{ ashford_ford: "Ashford Ridge" }}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={vi.fn()}
      />,
    );

    // 3 Wards rendered
    expect(screen.getByText("Left Ward (Vanguard)")).toBeInTheDocument();
    expect(screen.getByText("Center (Main Battle)")).toBeInTheDocument();
    expect(screen.getByText("Right Ward (Rearguard)")).toBeInTheDocument();

    // Cohorts rendered
    expect(screen.getByText(/Vanguard Spearmen/i)).toBeInTheDocument();
    expect(screen.getByText(/Shieldwall Spearmen/i)).toBeInTheDocument();

    // Find stepper plus button on first rank slot
    const plusButtons = screen.getAllByRole("button", { name: "+" });
    expect(plusButtons.length).toBeGreaterThan(0);

    fireEvent.click(plusButtons[0]!);
    expect(mockState.updateCohortCount).toHaveBeenCalledWith("left", "front", 50);
  });

  it("renders doctrine selections and updates tactic when selected", () => {
    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{ ashford_ford: "Ashford Ridge" }}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={vi.fn()}
      />,
    );

    // Doctrine cards should be visible in right pillar
    expect(screen.getByText("Shield-Wall Anchor")).toBeInTheDocument();
    expect(screen.getByText("Boar's Snout Wedge Shock")).toBeInTheDocument();

    // Click on Boar's Snout Wedge Shock
    const boarsSnout = screen.getByText("Boar's Snout Wedge Shock").closest("div");
    fireEvent.click(boarsSnout!);

    expect(mockState.setActiveDoctrine).toHaveBeenCalledWith("press");
  });

  it("renders the clash manuscript when a receipt report is open", () => {
    mockState.receiptReport = {
      battle_id: "battle-1",
      campaign_turn: 1,
      exchange_index: 1,
      total_exchange: 1,
      own_losses: { infantry: 42 },
      opponent_strength: { minimum: 900, maximum: 1200 },
      outcome: null,
    };

    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{ ashford_ford: "Ashford Ridge" }}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={vi.fn()}
      />,
    );

    expect(screen.getByText("Wave 1 Clash Manuscript")).toBeInTheDocument();
    expect(screen.getByText("42 fallen")).toBeInTheDocument();
  });

  it("renders the aftermath when the battle is resolved", () => {
    mockState.aftermath = {
      outcome: "attacker_victory",
      totalOwnLosses: 345,
      enemyStrengthRemaining: { minimum: 800, maximum: 900 },
    };

    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{ ashford_ford: "Ashford Ridge" }}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={vi.fn()}
      />,
    );

    expect(screen.getByText("Attacker Victory")).toBeInTheDocument();
    expect(screen.getByText("345")).toBeInTheDocument();
    expect(screen.getByText("800–900")).toBeInTheDocument();
  });

  it("shows a retryable error instead of a battle when loading fails", () => {
    mockState.battle = undefined;
    mockState.odds = null;
    mockState.loadErrorMessage = "The battle report could not be loaded.";

    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{}}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(screen.getByRole("alert")).toHaveTextContent("could not be loaded");
    expect(mockState.retryLoad).toHaveBeenCalled();
  });

  it("opens the speech before the battle and lets the player say nothing", () => {
    mockState.canAddressTroops = true;

    render(
      <StrategyWarCouncilScreen
        playthroughId="test-pt"
        battleId="battle-1"
        regionNames={{ ashford_ford: "Ashford Ridge" }}
        world={{ rivals: [], armies: [] }}
        onReturnToMap={vi.fn()}
      />,
    );

    expect(screen.getByRole("dialog", { name: "Address your host" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Say nothing" }));
    expect(screen.queryByRole("dialog", { name: "Address your host" })).toBeNull();
  });
});
