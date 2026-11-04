import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSceneDialog } from "../../../../hooks/useSceneDialog";
import { useSimulationWorld } from "../../../../hooks/useSimulationWorld";
import { StrategySceneDialog } from "../StrategySceneDialog";

vi.mock("../../../../hooks/useSceneDialog");
vi.mock("../../../../hooks/useSimulationWorld");

const mockUseSceneDialog = vi.mocked(useSceneDialog);
const mockUseSimulationWorld = vi.mocked(useSimulationWorld);

describe("StrategySceneDialog Full Stage", () => {
  const baseScene = {
    scene_id: "scene-1",
    scene_type: "negotiation",
    status: "opened" as const,
    turn: 4,
    is_declinable: true,
    situation: { summary: "Valdren frontier disputes.", facts: [] },
    participants: [
      {
        participant_id: "mira",
        kind: "leader",
        name: "Queen Mira",
        trait_ids: ["cautious"],
      },
    ],
    transcript: [
      {
        sequence: 1,
        player_text: "Let us discuss peace.",
        leader_text: "State your concessions.",
      },
    ],
    exchanges_remaining: 5,
    pending_proposal: {
      proposer_id: "mira",
      counterpart_id: "aldric",
      is_confirmed_by_player: false,
      is_confirmed_by_counterpart: true,
      terms: [
        {
          kind: "non_aggression" as const,
          faction_a: "mira",
          faction_b: "aldric",
          duration_turns: 3,
        },
      ],
    },
    pending_proposal_sequence: 1,
    outcome: null,
  };

  const baseWorld = {
    ruler: { name: "King Alden IV" },
    my_faction: {
      id: "f-valenreach",
      name: "Valenreach",
      treasury: 450,
      total_levies: 12500,
    },
    rivals: [
      {
        faction_id: "mira",
        name: "Dunmere",
        leader_name: "Queen Mira",
        relation: "peace",
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSimulationWorld.mockReturnValue({
      data: baseWorld,
    } as unknown as ReturnType<typeof useSimulationWorld>);
  });

  it("renders stage with dossier, chamber, console, and allows signing terms", () => {
    const handleDecide = vi.fn();
    const handleSend = vi.fn();

    mockUseSceneDialog.mockReturnValue({
      scene: baseScene,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: handleSend,
      },
      decision: {
        decide: handleDecide,
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />);

    expect(screen.getByText(/Peace Talks with Queen Mira/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Queen Mira" })).toBeInTheDocument();
    expect(screen.getByText(/State your concessions/i)).toBeInTheDocument();
    expect(screen.getByText("King Alden IV")).toBeInTheDocument();

    // Toggle drawer via Offer button
    fireEvent.click(screen.getByRole("button", { name: /^offer$/i }));
    expect(screen.getByText("On the Table")).toBeInTheDocument();

    // Sign the pact
    const signBtn = screen.getByRole("button", { name: /sign the pact/i });
    fireEvent.click(signBtn);
    expect(handleDecide).toHaveBeenCalledWith({
      isConfirmed: true,
      proposalSequence: 1,
    });
  });

  it("shows the grudges the leader has voiced, and none before", () => {
    const dialogState = {
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: { decide: vi.fn(), isDeciding: false, errorMessage: null },
    };
    mockUseSceneDialog.mockReturnValue({ ...dialogState, scene: baseScene });
    const { rerender } = render(
      <StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />,
    );
    expect(screen.queryByRole("region", { name: /held against you/i })).not.toBeInTheDocument();

    mockUseSceneDialog.mockReturnValue({
      ...dialogState,
      scene: {
        ...baseScene,
        voiced_grudges: [
          {
            text: "You broke the truce.",
            band: "burning" as const,
            is_inherited: true,
            predecessor_name: "King Aldric",
          },
        ],
      },
    });
    rerender(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />);

    expect(screen.getByText("You broke the truce.")).toBeInTheDocument();
    expect(screen.getByText(/inherited from King Aldric/i)).toBeInTheDocument();
  });

  it("allows submitting player dialogue via the console", () => {
    const handleSend = vi.fn();

    mockUseSceneDialog.mockReturnValue({
      scene: baseScene,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: handleSend,
      },
      decision: {
        decide: vi.fn(),
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />);

    const input = screen.getByPlaceholderText(/speak to the ruler/i);
    fireEvent.change(input, { target: { value: "We seek a lasting truce." } });

    const speakBtn = screen.getByRole("button", { name: /^speak$/i });
    fireEvent.click(speakBtn);

    expect(handleSend).toHaveBeenCalledWith("We seek a lasting truce.");
  });

  it("allows breaking talks from console with confirmation", () => {
    const handleDecide = vi.fn();

    mockUseSceneDialog.mockReturnValue({
      scene: baseScene,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: handleDecide,
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /break talks/i }));
    expect(screen.getByText(/Are you sure you want to walk away/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirm break talks/i }));
    expect(handleDecide).toHaveBeenCalledWith({ isConfirmed: false });
  });

  it("calls onClose when exiting a finished scene from the header", () => {
    const handleClose = vi.fn();

    mockUseSceneDialog.mockReturnValue({
      scene: baseScene,
      isFinished: true,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: vi.fn(),
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={handleClose} />);

    fireEvent.click(screen.getByRole("button", { name: /exit to encampment/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("keeps the header exit disabled until the scene is finished", () => {
    const handleClose = vi.fn();

    mockUseSceneDialog.mockReturnValue({
      scene: baseScene,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: vi.fn(),
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={handleClose} />);

    expect(screen.getByRole("button", { name: /exit to encampment/i })).toBeDisabled();
    expect(handleClose).not.toHaveBeenCalled();
  });

  it("renders ratification overlay when isFinished is true", () => {
    const handleClose = vi.fn();

    mockUseSceneDialog.mockReturnValue({
      scene: {
        ...baseScene,
        status: "resolved",
        outcome: {
          kind: "terms_card",
          result: "agreed",
          terms_card: baseScene.pending_proposal,
        },
      },
      isFinished: true,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: vi.fn(),
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={handleClose} />);

    expect(screen.getByText("Treaty Sealed & Ratified")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /return to campaign map/i }));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it("returns null when scene is missing or not negotiation", () => {
    mockUseSceneDialog.mockReturnValue({
      scene: undefined,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: vi.fn(),
        isDeciding: false,
        errorMessage: null,
      },
    });

    const { container } = render(
      <StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders peace scene with peace conference header and peace terms in treaty drawer", () => {
    const handleDecide = vi.fn();
    const peaceScene = {
      ...baseScene,
      scene_type: "peace",
      pending_proposal: {
        proposer_id: "mira",
        counterpart_id: "aldric",
        is_confirmed_by_player: false,
        is_confirmed_by_counterpart: true,
        terms: [
          {
            kind: "peace" as const,
            faction_a: "mira",
            faction_b: "aldric",
            tier: "medium" as const,
            duration_turns: 16,
            guarantor_ids: ["Dunmere League"],
          },
          {
            kind: "pay_gold" as const,
            payer_id: "aldric",
            payee_id: "mira",
            amount: 150,
          },
          {
            kind: "tribute" as const,
            payer_id: "aldric",
            payee_id: "mira",
            gold_per_turn: 25,
            duration_turns: 8,
          },
          {
            kind: "cede_region" as const,
            from_faction_id: "aldric",
            to_faction_id: "mira",
            region_id: "reg-vale",
            region_name: "Green Vale",
          },
          {
            kind: "release_prisoners" as const,
            holder_id: "mira",
            recipient_id: "aldric",
            prisoner_ids: ["pris-1"],
            ransom_gold: 50,
          },
          {
            kind: "hostage" as const,
            giver_id: "aldric",
            holder_id: "mira",
            leader_id: "lord-edward",
            character_name: "Lord Edward",
            duration_turns: 10,
          },
        ],
      },
    };

    mockUseSceneDialog.mockReturnValue({
      scene: peaceScene,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: handleDecide,
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-peace" onClose={vi.fn()} />);

    expect(screen.getByText(/Peace Conference with Queen Mira/i)).toBeInTheDocument();

    // Toggle drawer via Offer button
    fireEvent.click(screen.getByRole("button", { name: /^offer$/i }));
    expect(screen.getByText("On the Table")).toBeInTheDocument();

    // Verify rich terms rendered in drawer
    expect(screen.getByText(/Medium/i)).toBeInTheDocument();
    expect(screen.getByText(/150g/i)).toBeInTheDocument();
    expect(screen.getByText(/25g/i)).toBeInTheDocument();
    expect(screen.getByText(/Green Vale/i)).toBeInTheDocument();
    expect(screen.getByText(/ransom of 50g/i)).toBeInTheDocument();
    expect(screen.getByText(/Lord Edward/i)).toBeInTheDocument();
  });

  it("renders emergency escape hatch when scene type is unsupported in awaiting_scene", () => {
    mockUseSimulationWorld.mockReturnValue({
      data: {
        ...baseWorld,
        status: "awaiting_scene",
      },
    } as unknown as ReturnType<typeof useSimulationWorld>);

    const handleDecide = vi.fn();
    mockUseSceneDialog.mockReturnValue({
      scene: {
        ...baseScene,
        scene_type: "unsupported_unknown_scene" as unknown as typeof baseScene.scene_type,
      },
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: handleDecide,
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-1" onClose={vi.fn()} />);

    expect(screen.getByText("Conference Unavailable")).toBeInTheDocument();
    const escapeButton = screen.getByRole("button", { name: /Break Talks & Resume Campaign/i });
    expect(escapeButton).toBeInTheDocument();
    fireEvent.click(escapeButton);
    expect(handleDecide).toHaveBeenCalledWith({ isConfirmed: false });
  });

  it("renders emergency escape hatch when scene fails to load in awaiting_scene", () => {
    mockUseSimulationWorld.mockReturnValue({
      data: {
        ...baseWorld,
        status: "awaiting_scene",
      },
    } as unknown as ReturnType<typeof useSimulationWorld>);

    const handleDecide = vi.fn();
    mockUseSceneDialog.mockReturnValue({
      scene: undefined,
      isFinished: false,
      isBusy: false,
      stream: {
        reply: "",
        pendingPlayerText: null,
        isStreaming: false,
        failureMessage: null,
        sendMessage: vi.fn(),
      },
      decision: {
        decide: handleDecide,
        isDeciding: false,
        errorMessage: null,
      },
    });

    render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-err" onClose={vi.fn()} />);

    expect(screen.getByText("Conference Unavailable")).toBeInTheDocument();
    const escapeButton = screen.getByRole("button", { name: /Break Talks & Resume Campaign/i });
    expect(escapeButton).toBeInTheDocument();
    fireEvent.click(escapeButton);
    expect(handleDecide).toHaveBeenCalledWith({ isConfirmed: false });
  });
  describe("revolt talk", () => {
    const revoltScene = {
      ...baseScene,
      scene_id: "scene-revolt",
      scene_type: "revolt_talk",
      situation: { summary: "The Guild Elder of Home speaks for the people.", facts: [] },
      participants: [
        { participant_id: "spokesperson_home", kind: "leader", name: "The Guild Elder", trait_ids: [] },
      ],
      pending_proposal: null,
    };

    function mockRevolt(overrides: Record<string, unknown> = {}, isFinished = false) {
      mockUseSceneDialog.mockReturnValue({
        scene: { ...revoltScene, ...overrides },
        isFinished,
        isBusy: false,
        stream: {
          reply: "",
          pendingPlayerText: null,
          isStreaming: false,
          failureMessage: null,
          sendMessage: vi.fn(),
        },
        decision: { decide: vi.fn(), isDeciding: false, errorMessage: null },
      });
    }

    it("opens as talks with the people and hides the treaty controls", () => {
      mockRevolt();

      render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-revolt" onClose={vi.fn()} />);

      expect(screen.getByRole("dialog", { name: "Talks with The Guild Elder" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /toggle treaty drawer/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /draft a clause/i })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /break talks/i })).toBeInTheDocument();
    });

    it("tells the player what the people were given when the talk ends", () => {
      mockRevolt({ status: "resolved", outcome: { kind: "choice", option_id: "charter" } }, true);

      render(<StrategySceneDialog playthroughId="pt-1" sceneId="scene-revolt" onClose={vi.fn()} />);

      expect(screen.getByText("The People Are Answered")).toBeInTheDocument();
      expect(screen.getByText(/A charter was granted/)).toBeInTheDocument();
    });
  });
});
