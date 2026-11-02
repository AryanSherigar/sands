import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { WardConfig, WardIdentifier } from "../../StrategyWarCouncil.types";
import { PlayerWardRanks } from "../PlayerWardRanks";

const mockWards: Record<WardIdentifier, WardConfig> = {
  left: {
    ward: "left",
    title: "Left Vanguard",
    stance: "hold",
    isAnchor: false,
    ranks: [
      {
        id: "c-left-1",
        troopType: "infantry",
        name: "Spearmen",
        count: 600,
        rankOrder: "front",
        tacticalRole: "Brace line",
      },
    ],
  },
  center: {
    ward: "center",
    title: "Center Main Battle",
    stance: "hold",
    isAnchor: true,
    ranks: [
      {
        id: "c-center-1",
        troopType: "infantry",
        name: "Heavy Foot",
        count: 800,
        rankOrder: "front",
        tacticalRole: "Shieldwall",
      },
      {
        id: "c-center-2",
        troopType: "archers_siege",
        name: "Longbows",
        count: 350,
        rankOrder: "middle",
        tacticalRole: "Volley fire",
      },
      {
        id: "c-center-3",
        troopType: "cavalry",
        name: "Dismounted Knights",
        count: 250,
        rankOrder: "rear",
        tacticalRole: "Rear shock",
      },
    ],
  },
  right: {
    ward: "right",
    title: "Right Rearguard",
    stance: "refuse",
    isAnchor: false,
    ranks: [
      {
        id: "c-right-1",
        troopType: "infantry",
        name: "Spearmen",
        count: 300,
        rankOrder: "front",
        tacticalRole: "Cover shallows",
      },
    ],
  },
};

describe("PlayerWardRanks", () => {
  it("renders 3 wards including anchor badge and 3 rank slots", () => {
    render(
      <PlayerWardRanks
        wards={mockWards}
        onUpdateCohortCount={vi.fn()}
        onReorderRank={vi.fn()}
        onSelectAnchor={vi.fn()}
      />,
    );

    // 1. Renders 3 wards
    expect(screen.getByText("Left Vanguard")).toBeInTheDocument();
    expect(screen.getByText("Center Main Battle")).toBeInTheDocument();
    expect(screen.getByText("Right Rearguard")).toBeInTheDocument();

    // 2. Tactic anchor badge
    expect(screen.getByText(/Tactic Anchor/i)).toBeInTheDocument();

    // 3. Renders 3 rank slots
    expect(screen.getAllByText("1st: Front Rank")[0]).toBeInTheDocument();
    expect(screen.getByText("2nd: Middle Rank")).toBeInTheDocument();
    expect(screen.getByText("3rd: Rear Shock")).toBeInTheDocument();
    expect(screen.getByText("Shieldwall")).toBeInTheDocument();
  });

  it("triggers onUpdateCohortCount when clicking + and − steppers", () => {
    const handleUpdateCohortCount = vi.fn();

    render(
      <PlayerWardRanks
        wards={mockWards}
        onUpdateCohortCount={handleUpdateCohortCount}
        onReorderRank={vi.fn()}
        onSelectAnchor={vi.fn()}
      />,
    );

    const plusButtons = screen.getAllByRole("button", { name: "+" });
    fireEvent.click(plusButtons[0]);
    expect(handleUpdateCohortCount).toHaveBeenCalledWith("left", "front", 50);

    const minusButtons = screen.getAllByRole("button", { name: "−" });
    fireEvent.click(minusButtons[0]);
    expect(handleUpdateCohortCount).toHaveBeenCalledWith("left", "front", -50);
  });

  it("triggers onReorderRank when clicking rank reordering buttons (▲ / ▼)", () => {
    const handleReorderRank = vi.fn();

    render(
      <PlayerWardRanks
        wards={mockWards}
        onUpdateCohortCount={vi.fn()}
        onReorderRank={handleReorderRank}
        onSelectAnchor={vi.fn()}
      />,
    );

    // Front rank of center ward should be able to move down to middle
    const downButtons = screen.getAllByRole("button", { name: "▼" });
    // First down button in center ward is for front rank
    const centerFrontDown = downButtons[1];
    fireEvent.click(centerFrontDown);
    expect(handleReorderRank).toHaveBeenCalledWith("center", "front", "middle");

    // Middle rank up button
    const upButtons = screen.getAllByRole("button", { name: "▲" });
    // Center middle up button
    const centerMiddleUp = upButtons.find((btn) => !btn.hasAttribute("disabled"));
    expect(centerMiddleUp).toBeDefined();
    if (centerMiddleUp) {
      fireEvent.click(centerMiddleUp);
      expect(handleReorderRank).toHaveBeenCalledWith("center", "middle", "front");
    }
  });

  it("triggers onSelectAnchor when selecting a ward", () => {
    const handleSelectAnchor = vi.fn();

    render(
      <PlayerWardRanks
        wards={mockWards}
        onUpdateCohortCount={vi.fn()}
        onReorderRank={vi.fn()}
        onSelectAnchor={handleSelectAnchor}
      />,
    );

    const leftWardCard = screen.getByText("Left Vanguard").closest(".ward-card");
    expect(leftWardCard).not.toBeNull();
    if (leftWardCard) {
      fireEvent.click(leftWardCard);
      expect(handleSelectAnchor).toHaveBeenCalledWith("left");
    }
  });
});
